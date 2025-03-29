from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import current_user, login_required
from datetime import datetime

from app import db
from app.organizer import bp # Import the blueprint
from app.organizer.forms import TournamentForm, TournamentPaymentForm, TournamentGiftsForm # Import relevant forms
from app.models import (Tournament, TournamentCategory, Registration, TournamentStatus,
                       TournamentTier, TournamentFormat) # Use new import path
from app.decorators import organizer_required
from app.helpers.registration import save_picture # Assuming this helper handles image saving

# --- Dashboard Routes ---

@bp.route('/dashboard')
@login_required
@organizer_required
def dashboard():
    # Get tournaments organized by this user or all if admin
    if current_user.is_admin():
        tournaments_query = Tournament.query
    else:
        tournaments_query = Tournament.query.filter_by(organizer_id=current_user.id)

    tournaments = tournaments_query.order_by(Tournament.start_date.desc()).all()

    # Split tournaments by status
    upcoming_tournaments = []
    ongoing_tournaments = []
    completed_tournaments = []

    # Get registration and payment data aggregates
    total_registrations = 0
    pending_payments = 0
    approved_payments = 0
    total_revenue = 0.0 # Use float for currency

    for tournament in tournaments:
        # Get category IDs for this tournament efficiently
        category_ids = [c.id for c in tournament.categories] # Assumes categories relationship is efficient enough or use query

        # Get registration counts efficiently
        regs_query = Registration.query.filter(Registration.category_id.in_(category_ids))

        total_regs_count = regs_query.count()
        pending_count = regs_query.filter(Registration.payment_status == 'uploaded', Registration.payment_verified == False).count()
        approved_count = regs_query.filter(Registration.payment_verified == True).count()
        # free_count = regs_query.filter(Registration.payment_status == 'free').count() # If needed

        registration_counts = {
            'total': total_regs_count,
            'pending': pending_count,
            'approved': approved_count,
            # 'free': free_count
        }
        tournament.registration_counts = registration_counts # Attach counts to object for template

        # Calculate revenue for completed tournaments
        revenue = 0.0
        if tournament.status == TournamentStatus.COMPLETED:
             # Sum registration fees for paid/verified registrations
             paid_regs = regs_query.filter(Registration.payment_status == 'paid', Registration.payment_verified == True).all()
             revenue = sum(reg.registration_fee or 0.0 for reg in paid_regs) # Handle potential None fee
             tournament.revenue = revenue
             total_revenue += revenue

        # Update overall stats
        total_registrations += total_regs_count
        pending_payments += pending_count
        approved_payments += approved_count

        # Split tournaments by status
        if tournament.status == TournamentStatus.UPCOMING:
            upcoming_tournaments.append(tournament)
        elif tournament.status == TournamentStatus.ONGOING:
            ongoing_tournaments.append(tournament)
        else:  # COMPLETED
            completed_tournaments.append(tournament)

    # Sort the lists
    upcoming_tournaments.sort(key=lambda t: t.start_date if t.start_date else datetime.min)
    ongoing_tournaments.sort(key=lambda t: t.end_date if t.end_date else datetime.min)
    completed_tournaments.sort(key=lambda t: t.end_date if t.end_date else datetime.min, reverse=True)

    # Counts for summary section
    total_tournaments = len(tournaments)
    upcoming_count = len(upcoming_tournaments)
    ongoing_count = len(ongoing_tournaments)
    completed_count = len(completed_tournaments)

    return render_template('organizer/dashboard.html',
                           title='Organizer Dashboard',
                           upcoming_tournaments=upcoming_tournaments,
                           ongoing_tournaments=ongoing_tournaments,
                           completed_tournaments=completed_tournaments,
                           total_tournaments=total_tournaments,
                           upcoming_count=upcoming_count,
                           ongoing_count=ongoing_count,
                           completed_count=completed_count,
                           total_registrations=total_registrations,
                           pending_payments=pending_payments,
                           approved_payments=approved_payments,
                           total_revenue=total_revenue,
                           now=datetime.now())


@bp.route('/dashboard/payments')
@login_required
@organizer_required
def payment_dashboard():
     # Get tournaments organized by current user or all if admin
    if current_user.is_admin():
        tournaments = Tournament.query.all()
    else:
        tournaments = Tournament.query.filter_by(organizer_id=current_user.id).all()
    tournament_ids = [t.id for t in tournaments]

    # Get categories for these tournaments
    categories = TournamentCategory.query.filter(TournamentCategory.tournament_id.in_(tournament_ids)).all()
    category_ids = [c.id for c in categories]

    # Get registrations for these categories
    all_registrations = Registration.query.filter(Registration.category_id.in_(category_ids)).all()

    # Summary counts
    pending_count = sum(1 for r in all_registrations if r.payment_status == 'uploaded' and not r.payment_verified)
    approved_count = sum(1 for r in all_registrations if r.payment_verified)
    rejected_count = sum(1 for r in all_registrations if r.payment_status == 'rejected')
    free_count = sum(1 for r in all_registrations if r.payment_status == 'free')

    # Total revenue by tournament
    tournament_revenue = {}
    for tournament in tournaments:
        revenue = 0.0
        # Efficiently get category IDs for the current tournament
        current_category_ids = [c.id for c in tournament.categories]
        if current_category_ids:
            # Sum fees directly from the database for verified registrations in this tournament's categories
            revenue = db.session.query(db.func.sum(Registration.registration_fee)).filter(
                Registration.category_id.in_(current_category_ids),
                Registration.payment_status == 'paid',
                Registration.payment_verified == True
            ).scalar() or 0.0
        tournament_revenue[tournament.id] = revenue

    # Recent payments (last 10 needing action or recently paid)
    recent_payments = Registration.query.filter(
        Registration.category_id.in_(category_ids),
        Registration.payment_status.in_(['paid', 'uploaded']) # Show uploaded (needs action) and recently paid
    ).order_by(
        # Prioritize uploaded proofs, then by upload/verification date
        db.case( (Registration.payment_status == 'uploaded', 0), else_=1 ),
        Registration.payment_proof_uploaded_at.desc().nullslast(), # Show newest uploads first
        Registration.payment_verified_at.desc().nullslast() # Show newest verified first
    ).limit(10).all()

    return render_template('organizer/payment_dashboard.html',
                          title='Payment Dashboard',
                          tournaments=tournaments,
                          pending_count=pending_count,
                          approved_count=approved_count,
                          rejected_count=rejected_count,
                          free_count=free_count,
                          tournament_revenue=tournament_revenue,
                          recent_payments=recent_payments)


# --- Tournament Management Routes ---

@bp.route('/tournament/create', methods=['GET', 'POST'])
@login_required
@organizer_required
def create_tournament():
    form = TournamentForm()

    if form.validate_on_submit():
        tournament = Tournament(organizer_id=current_user.id) # Assign organizer immediately

        # Populate basic fields
        form.populate_obj(tournament)

        # Convert string values to enums properly
        tournament.tier = TournamentTier[form.tier.data] if form.tier.data else None
        tournament.format = TournamentFormat[form.format.data] if form.format.data else None
        tournament.status = TournamentStatus[form.status.data] if form.status.data else TournamentStatus.UPCOMING

        # Handle image uploads using helper
        if form.logo.data:
            tournament.logo = save_picture(form.logo.data, 'tournament_logos')
        if form.banner.data:
            tournament.banner = save_picture(form.banner.data, 'tournament_banners')
        if form.payment_qr_code.data:
             tournament.payment_qr_code = save_picture(form.payment_qr_code.data, 'payment_qr_codes')
        if form.door_gifts_image.data:
             tournament.door_gifts_image = save_picture(form.door_gifts_image.data, 'door_gifts_images')

        try:
            db.session.add(tournament)
            db.session.commit()
            flash('Tournament created successfully! Now add categories.', 'success')
            # Redirect to category editing page for the new tournament
            return redirect(url_for('organizer.edit_categories', id=tournament.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating tournament: {e}', 'danger')

    # For GET requests or validation errors
    return render_template('organizer/create_tournament.html', # Consider renaming template if combined with edit
                           title='Create Tournament',
                           form=form)


@bp.route('/tournament/<int:id>')
@login_required
@organizer_required
def tournament_detail(id):
    tournament = Tournament.query.get_or_404(id)

    # Check if current user is the organizer or an admin
    if not current_user.is_admin() and tournament.organizer_id != current_user.id:
        flash('You do not have permission to view this tournament management page.', 'danger')
        return redirect(url_for('organizer.dashboard'))

    # Get categories for this tournament
    categories = tournament.categories.order_by(TournamentCategory.display_order).all()

    # Get registrations by category (only count approved/paid for display?)
    registrations = {}
    registration_counts = {}
    for category in categories:
        # Example: Count only paid/verified registrations for capacity display
        paid_registrations = Registration.query.filter_by(
            category_id=category.id,
            payment_status='paid',
            payment_verified=True
        ).all()
        registrations[category.id] = paid_registrations # Or maybe all regs depending on need

        # Count participants based on doubles/singles
        if category.is_doubles():
            registration_counts[category.id] = len(paid_registrations) * 2
        else:
            registration_counts[category.id] = len(paid_registrations)

    return render_template('organizer/tournament_detail.html',
                           title=f'Manage: {tournament.name}',
                           tournament=tournament,
                           categories=categories,
                           registrations=registrations, # Pass relevant registrations
                           registration_counts=registration_counts)


@bp.route('/tournament/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@organizer_required
def edit_tournament(id):
    tournament = Tournament.query.get_or_404(id)

    # Check permission
    if not current_user.is_admin() and tournament.organizer_id != current_user.id:
        flash('You do not have permission to edit this tournament.', 'danger')
        return redirect(url_for('organizer.tournament_detail', id=tournament.id))

    form = TournamentForm(obj=tournament) # Initialize with existing data

    if form.validate_on_submit():
        # Populate basic fields from form
        form.populate_obj(tournament)

        # Convert string values to enums properly
        tournament.tier = TournamentTier[form.tier.data] if form.tier.data else None
        tournament.format = TournamentFormat[form.format.data] if form.format.data else None
        tournament.status = TournamentStatus[form.status.data] if form.status.data else None

        # Handle image uploads only if new files are provided
        if form.logo.data:
            tournament.logo = save_picture(form.logo.data, 'tournament_logos')
        if form.banner.data:
            tournament.banner = save_picture(form.banner.data, 'tournament_banners')
        if form.payment_qr_code.data:
             tournament.payment_qr_code = save_picture(form.payment_qr_code.data, 'payment_qr_codes')
        if form.door_gifts_image.data:
             tournament.door_gifts_image = save_picture(form.door_gifts_image.data, 'door_gifts_images')

        try:
            db.session.commit()
            flash('Tournament details updated successfully!', 'success')
            # Redirect back to the detail/management page, or maybe category edit?
            return redirect(url_for('organizer.edit_tournament', id=id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating tournament: {e}', 'danger')

    # For GET requests, ensure enums are pre-selected correctly
    if request.method == 'GET':
        if tournament.tier:
            form.tier.data = tournament.tier.name
        if tournament.format:
            form.format.data = tournament.format.name
        if tournament.status:
            form.status.data = tournament.status.name

    return render_template('organizer/edit_tournament.html', # Can use same template as create
                           title=f'Edit Tournament - {tournament.name}',
                           tournament=tournament,
                           form=form,
                           is_edit=True) # Flag for template logic if needed


@bp.route('/tournament/<int:id>/payment_settings', methods=['GET', 'POST'])
@login_required
@organizer_required
def payment_settings(id):
    tournament = Tournament.query.get_or_404(id)

    # Check permission
    if not current_user.is_admin() and tournament.organizer_id != current_user.id:
        flash('You do not have permission to edit payment settings for this tournament.', 'danger')
        return redirect(url_for('organizer.tournament_detail', id=id))

    form = TournamentPaymentForm(obj=tournament)

    if form.validate_on_submit():
        form.populate_obj(tournament) # Update fields from form

        # Handle QR code upload
        if form.payment_qr_code.data:
            tournament.payment_qr_code = save_picture(form.payment_qr_code.data, 'payment_qr_codes')

        try:
            db.session.commit()
            flash('Payment settings updated successfully!', 'success')
            return redirect(url_for('organizer.tournament_detail', id=id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating payment settings: {e}', 'danger')

    return render_template('organizer/payment_settings.html',
                          title='Payment Settings',
                          tournament=tournament,
                          form=form)


@bp.route('/tournament/<int:id>/door_gifts', methods=['GET', 'POST'])
@login_required
@organizer_required
def door_gifts(id):
    tournament = Tournament.query.get_or_404(id)

    # Check permission
    if not current_user.is_admin() and tournament.organizer_id != current_user.id:
        flash('You do not have permission to edit door gifts for this tournament.', 'danger')
        return redirect(url_for('organizer.tournament_detail', id=id))

    form = TournamentGiftsForm(obj=tournament)

    if form.validate_on_submit():
        form.populate_obj(tournament) # Update fields from form

        # Handle door gifts image upload
        if form.door_gifts_image.data:
            tournament.door_gifts_image = save_picture(form.door_gifts_image.data, 'door_gifts_images')

        try:
            db.session.commit()
            flash('Door gifts information updated successfully!', 'success')
            return redirect(url_for('organizer.tournament_detail', id=id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating door gifts: {e}', 'danger')

    return render_template('organizer/door_gifts.html',
                          title='Door Gifts',
                          tournament=tournament,
                          form=form)