from flask import render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
import os
import math
import random
from datetime import datetime, timedelta

from app import db
from app.organizer import bp
from app.organizer.forms import (TournamentForm, CategoryForm, SeedingForm, 
                                MatchForm, ScoreForm, BracketGenerationForm,
                                CompleteMatchForm)
from app.models import (Tournament, TournamentCategory, Match, MatchScore, 
                       Registration, PlayerProfile, User, TournamentStatus,
                       TournamentTier, TournamentFormat, CategoryType, Prize, PrizeType)
from app.services import BracketService, PlacingService, PrizeService, RegistrationService

from app.decorators import organizer_required

from app.helpers.tournament import (
    _generate_group_stage,
    _create_round_robin_matches,
    _generate_knockout_from_groups,
    _generate_single_elimination,
    _create_knockout_matches
)

from app.helpers.registration import save_picture

@bp.route('/registrations')
@login_required
@organizer_required
def view_registrations():
    # Get tournaments organized by current user
    tournaments = Tournament.query.filter_by(organizer_id=current_user.id).all()
    tournament_ids = [t.id for t in tournaments]
    
    # Get categories for these tournaments
    categories = TournamentCategory.query.filter(TournamentCategory.tournament_id.in_(tournament_ids)).all()
    category_ids = [c.id for c in categories]
    
    # Get registrations for these categories
    registrations = Registration.query.filter(Registration.category_id.in_(category_ids)).all()
    
    # Filter by status if requested
    status_filter = request.args.get('status', 'pending')
    if status_filter == 'pending':
        registrations = [r for r in registrations if r.payment_status == 'uploaded' and not r.payment_verified]
    elif status_filter == 'approved':
        registrations = [r for r in registrations if r.payment_verified]
    elif status_filter == 'rejected':
        registrations = [r for r in registrations if r.payment_status == 'rejected']
    
    # Filter by tournament if requested
    tournament_filter = request.args.get('tournament', 'all')
    if tournament_filter != 'all' and tournament_filter.isdigit():
        tournament_id = int(tournament_filter)
        if tournament_id in tournament_ids:
            filtered_category_ids = [c.id for c in categories if c.tournament_id == tournament_id]
            registrations = [r for r in registrations if r.category_id in filtered_category_ids]
    
    return render_template('organizer/view_registrations.html',
                          title='Tournament Registrations',
                          registrations=registrations,
                          status_filter=status_filter,
                          tournament_filter=tournament_filter,
                          all_tournaments=tournaments)

@bp.route('/registration/<int:id>')
@login_required
@organizer_required
def view_registration(id):
    registration = Registration.query.get_or_404(id)
    #registration.send_confirmation_emails()
    # Ensure the tournament belongs to this organizer
    tournament = registration.category.tournament
    if tournament.organizer_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to view this registration.', 'danger')
        return redirect(url_for('organizer.view_registrations'))
    
    category = registration.category
    
    # Get the user who verified the payment if applicable
    verified_by_user = None
    if registration.payment_verified_by:
        verified_by_user = User.query.get(registration.payment_verified_by)
    
    return render_template('organizer/view_registration.html',
                          title='View Registration',
                          registration=registration,
                          tournament=tournament,
                          category=category,
                          verified_by_user=verified_by_user)

@bp.route('/registration/<int:id>/verify', methods=['POST'])
@login_required
@organizer_required
def verify_registration(id):
    registration = Registration.query.get_or_404(id)
    
    # Ensure the tournament belongs to this organizer
    tournament = registration.category.tournament
    if tournament.organizer_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to verify this registration.', 'danger')
        return redirect(url_for('organizer.view_registrations'))
    
    # Verify payment
    registration.payment_verified = True
    registration.payment_verified_at = datetime.utcnow()
    registration.payment_verified_by = current_user.id
    registration.payment_status = 'paid'
    registration.is_approved = True
    
    db.session.commit()
    
    flash('Registration payment verified and approved!', 'success')
    return redirect(url_for('organizer.view_registration', id=id))

@bp.route('/registration/<int:id>/reject', methods=['POST'])
@login_required
@organizer_required
def reject_registration(id):
    registration = Registration.query.get_or_404(id)
    
    # Ensure the tournament belongs to this organizer
    tournament = registration.category.tournament
    if tournament.organizer_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to verify this registration.', 'danger')
        return redirect(url_for('organizer.view_registrations'))
    
    # Get the rejection reason from form
    rejection_reason = request.form.get('rejection_reason', '')

    # Verify payment
    registration.payment_verified = False
    registration.payment_verified_at = datetime.utcnow()
    registration.payment_verified_by = current_user.id
    registration.payment_status = 'rejected'
    registration.is_approved = False
    registration.payment_rejection_reason = rejection_reason
    
    db.session.commit()
    
    flash(f'Registration for {registration.team_name} has been rejected.', 'warning')
    return redirect(url_for('organizer.view_registration', id=id))

@bp.route('/tournament/<int:id>/payment_settings', methods=['GET', 'POST'])
@login_required
@organizer_required
def payment_settings(id):
    tournament = Tournament.query.get_or_404(id)
    
    # Ensure the tournament belongs to this organizer
    if tournament.organizer_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to edit this tournament.', 'danger')
        return redirect(url_for('organizer.dashboard'))
    
    from app.organizer.forms import TournamentPaymentForm
    form = TournamentPaymentForm(obj=tournament)
    
    if form.validate_on_submit():
        tournament.payment_bank_name = form.payment_bank_name.data
        tournament.payment_account_number = form.payment_account_number.data
        tournament.payment_account_name = form.payment_account_name.data
        tournament.payment_reference_prefix = form.payment_reference_prefix.data
        tournament.payment_instructions = form.payment_instructions.data
        
        # Handle QR code upload
        if form.payment_qr_code.data:
            from app.organizer.routes import save_tournament_image
            tournament.payment_qr_code = save_tournament_image(form.payment_qr_code.data, 'payment_qr_codes')
        
        db.session.commit()
        
        flash('Payment settings updated successfully!', 'success')
        return redirect(url_for('organizer.tournament_detail', id=id))
    
    return render_template('organizer/payment_settings.html',
                          title='Payment Settings',
                          tournament=tournament,
                          form=form)

@bp.route('/tournament/<int:id>/door_gifts', methods=['GET', 'POST'])
@login_required
@organizer_required
def door_gifts(id):
    tournament = Tournament.query.get_or_404(id)
    
    # Ensure the tournament belongs to this organizer
    if tournament.organizer_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to edit this tournament.', 'danger')
        return redirect(url_for('organizer.dashboard'))
    
    from app.organizer.forms import TournamentGiftsForm
    form = TournamentGiftsForm(obj=tournament)
    
    if form.validate_on_submit():
        tournament.door_gifts = form.door_gifts.data
        
        # Handle door gifts image upload
        if form.door_gifts_image.data:
            from app.organizer.routes import save_tournament_image
            tournament.door_gifts_image = save_tournament_image(form.door_gifts_image.data, 'door_gifts_images')
        
        db.session.commit()
        
        flash('Door gifts information updated successfully!', 'success')
        return redirect(url_for('organizer.tournament_detail', id=id))
    
    return render_template('organizer/door_gifts.html',
                          title='Door Gifts',
                          tournament=tournament,
                          form=form)

@bp.route('/dashboard/payments')
@login_required
@organizer_required
def payment_dashboard():
    # Get tournaments organized by current user
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
        revenue = 0
        for category in tournament.categories:
            # Count only verified payments
            verified_registrations = Registration.query.filter_by(
                category_id=category.id, 
                payment_status='paid',
                payment_verified=True
            ).count()
            revenue += verified_registrations * category.registration_fee
        tournament_revenue[tournament.id] = revenue
    
    # Recent payments (last 10)
    recent_payments = Registration.query.filter(
        Registration.category_id.in_(category_ids),
        Registration.payment_status.in_(['paid', 'uploaded'])
    ).order_by(Registration.payment_proof_uploaded_at.desc()).limit(10).all()
    
    return render_template('organizer/payment_dashboard.html',
                          title='Payment Dashboard',
                          tournaments=tournaments,
                          pending_count=pending_count,
                          approved_count=approved_count,
                          rejected_count=rejected_count,
                          free_count=free_count,
                          tournament_revenue=tournament_revenue,
                          recent_payments=recent_payments)


def save_picture(picture, subfolder='tournament_pics'):
    # Generate a secure filename
    filename = secure_filename(picture.filename)
    
    # Generate a unique filename with timestamp
    unique_filename = f"{subfolder}_{int(datetime.utcnow().timestamp())}_{filename}"
    
    # Create full path
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder, unique_filename)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Save the file
    picture.save(file_path)
    
    # Return the relative path for the database
    return os.path.join('uploads', subfolder, unique_filename)

@bp.route('/dashboard')
@login_required
@organizer_required
def dashboard():
    # Get tournaments organized by this user
    tournaments = Tournament.query.filter_by(organizer_id=current_user.id).order_by(Tournament.start_date.desc()).all()
    
    # Split tournaments by status
    upcoming_tournaments = []
    ongoing_tournaments = []
    completed_tournaments = []
    
    # Get registration and payment data
    total_registrations = 0
    pending_payments = 0
    approved_payments = 0
    total_revenue = 0
    
    for tournament in tournaments:
        # Get all categories for this tournament
        categories = tournament.categories.all()
        category_ids = [c.id for c in categories]
        
        # Get all registrations for these categories
        registrations = Registration.query.filter(Registration.category_id.in_(category_ids)).all()
        
        # Count registrations and payment status
        registration_counts = {
            'total': len(registrations),
            'pending': sum(1 for r in registrations if r.payment_status == 'uploaded' and not r.payment_verified),
            'approved': sum(1 for r in registrations if r.payment_verified),
            'free': sum(1 for r in registrations if r.payment_status == 'free')
        }
        
        # Add registration counts to tournament object
        tournament.registration_counts = registration_counts
        
        # Calculate revenue for completed tournaments
        if tournament.status == TournamentStatus.COMPLETED:
            revenue = 0
            for category in categories:
                paid_registrations = Registration.query.filter_by(
                    category_id=category.id, 
                    payment_status='paid'
                ).count()
                revenue += paid_registrations * category.registration_fee
            tournament.revenue = revenue
            total_revenue += revenue
        
        # Update overall stats
        total_registrations += registration_counts['total']
        pending_payments += registration_counts['pending']
        approved_payments += registration_counts['approved']
        
        # Split tournaments by status
        if tournament.status == TournamentStatus.UPCOMING:
            upcoming_tournaments.append(tournament)
        elif tournament.status == TournamentStatus.ONGOING:
            ongoing_tournaments.append(tournament)
        else:  # COMPLETED
            completed_tournaments.append(tournament)
    
    # Sort the lists
    upcoming_tournaments.sort(key=lambda t: t.start_date)
    ongoing_tournaments.sort(key=lambda t: t.end_date)
    completed_tournaments.sort(key=lambda t: t.end_date, reverse=True)
    
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

@bp.route('/<int:id>/manage_category/<int:category_id>', methods=['GET', 'POST'])
@login_required
def manage_category(id, category_id):
    """Admin page to manage a tournament category"""
    # Ensure the current user is the tournament organizer
    tournament = Tournament.query.get_or_404(id)
    if tournament.organizer_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to manage this tournament.', 'danger')
        return redirect(url_for('main.tournament_detail', id=id))
    
    category = TournamentCategory.query.get_or_404(category_id)
    
    if request.method == 'POST':
        # Update category settings
        if 'update_settings' in request.form:
            category.max_participants = request.form.get('max_participants', type=int)
            category.points_awarded = request.form.get('points_awarded', type=int)
            category.prize_percentage = request.form.get('prize_percentage', type=float)
            
            # Update DUPR rating restrictions
            category.min_dupr_rating = request.form.get('min_dupr_rating', type=float) or None
            category.max_dupr_rating = request.form.get('max_dupr_rating', type=float) or None
            
            # Update age restrictions
            category.min_age = request.form.get('min_age', type=int) or None
            category.max_age = request.form.get('max_age', type=int) or None
            
            # Update gender restriction
            category.gender_restriction = request.form.get('gender_restriction') or None
            
            # Update format-specific settings
            if tournament.format == 'GROUP_KNOCKOUT':
                category.group_count = request.form.get('group_count', type=int) or 0
                category.teams_per_group = request.form.get('teams_per_group', type=int) or 0
                category.teams_advancing_per_group = request.form.get('teams_advancing_per_group', type=int) or 0
            
            db.session.commit()
            flash('Category settings updated successfully.', 'success')
        
        # Update custom prize distribution
        elif 'update_prize_distribution' in request.form:
            prize_distribution = {}
            for key in request.form:
                if key.startswith('prize_'):
                    place_range = key[6:]  # Remove 'prize_' prefix
                    percentage = request.form.get(key, type=float)
                    if percentage:
                        prize_distribution[place_range] = percentage
            
            # Validate that percentages add up to 100%
            if sum(prize_distribution.values()) != 100:
                flash('Prize distribution percentages must add up to 100%.', 'danger')
            else:
                category.prize_distribution = prize_distribution
                db.session.commit()
                flash('Prize distribution updated successfully.', 'success')
        
        # Update custom points distribution
        elif 'update_points_distribution' in request.form:
            points_distribution = {}
            for key in request.form:
                if key.startswith('points_'):
                    place_range = key[7:]  # Remove 'points_' prefix
                    percentage = request.form.get(key, type=float)
                    if percentage:
                        points_distribution[place_range] = percentage
            
            # No need to validate percentages for points
            category.points_distribution = points_distribution
            db.session.commit()
            flash('Points distribution updated successfully.', 'success')
        
        # Generate bracket
        elif 'generate_bracket' in request.form:
            bracket_type = request.form.get('bracket_type')
            if bracket_type == 'generate_groups':
                # Generate group stage first
                success = _generate_group_stage(category)
                if success:
                    flash('Group stage generated successfully.', 'success')
                else:
                    flash('Failed to generate group stage.', 'danger')
            elif bracket_type == 'generate_knockout':
                # Generate knockout stage
                if tournament.format == 'GROUP_KNOCKOUT':
                    # For group + knockout, use group results to seed knockout
                    success = _generate_knockout_from_groups(category)
                else:
                    # For single elimination, generate from registrations
                    success = _generate_single_elimination(category)
                
                if success:
                    flash('Knockout bracket generated successfully.', 'success')
                else:
                    flash('Failed to generate knockout bracket.', 'danger')
            else:
                flash('Invalid bracket type.', 'danger')
    
    # Get all registrations for this category
    registrations = Registration.query.filter_by(category_id=category_id).all()
    
    # Get existing matches for this category
    matches = Match.query.filter_by(category_id=category_id).order_by(Match.stage, Match.round).all()
    
    # Get groups if they exist
    groups = Group.query.filter_by(category_id=category_id).all()
    
    return render_template('tournament/admin/manage_category.html',
                          title=f"Manage {category.category_type.value}",
                          tournament=tournament,
                          category=category,
                          registrations=registrations,
                          matches=matches,
                          groups=groups)

@bp.route('/<int:id>/generate_all_brackets', methods=['POST'])
@login_required
def generate_all_brackets(id):
    """Generate brackets for all categories in a tournament"""
    # Ensure the current user is the tournament organizer
    tournament = Tournament.query.get_or_404(id)
    if tournament.organizer_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to manage this tournament.', 'danger')
        return redirect(url_for('main.tournament_detail', id=id))
    
    for category in tournament.categories:
        if tournament.format == 'GROUP_KNOCKOUT':
            # Generate group stage first
            _generate_group_stage(category)
            # Then generate knockout brackets from group results
            _generate_knockout_from_groups(category)
        else:
            # Generate single elimination bracket
            _generate_single_elimination(category)
    
    flash('Brackets generated for all categories.', 'success')
    return redirect(url_for('tournament.admin.manage_tournament', id=id))

@bp.route('/<int:id>/distribute_prize_money', methods=['POST'])
@login_required
def distribute_prize_money(id):
    """Distribute prize money across categories based on percentages"""
    # Ensure the current user is the tournament organizer
    tournament = Tournament.query.get_or_404(id)
    if tournament.organizer_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to manage this tournament.', 'danger')
        return redirect(url_for('main.tournament_detail', id=id))
    
    # Use our service to distribute prize money
    categories = PrizeService.distribute_prize_pool(id)
    
    flash(f'Prize money distributed among {len(categories)} categories.', 'success')
    return redirect(url_for('tournament.admin.manage_tournament', id=id))

@bp.route('/<int:id>/update_match/<int:match_id>', methods=['POST'])
@login_required
def update_match(id, match_id):
    """Update match scores and results"""
    # Ensure the current user is the tournament organizer
    tournament = Tournament.query.get_or_404(id)
    if tournament.organizer_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to manage this tournament.', 'danger')
        return redirect(url_for('tournament.match_detail', id=id, match_id=match_id))
    
    match = Match.query.get_or_404(match_id)
    
    # Update match scores
    set_count = int(request.form.get('set_count', 0))
    
    # Remove existing scores
    MatchScore.query.filter_by(match_id=match_id).delete()
    
    # Add new scores
    for i in range(1, set_count + 1):
        player1_score = request.form.get(f'player1_score_{i}', type=int) or 0
        player2_score = request.form.get(f'player2_score_{i}', type=int) or 0
        
        score = MatchScore(
            match_id=match_id,
            set_number=i,
            player1_score=player1_score,
            player2_score=player2_score
        )
        db.session.add(score)
    
    # Determine match winner
    if 'set_winner' in request.form:
        is_player1_winner = request.form.get('set_winner') == 'player1'
        match.set_winner(is_player1_winner)
        match.completed = True
        
        # If this is a group match, update group standings
        if match.group_id:
            BracketService.update_group_standings(match.group_id)
        
        # If not a group match, advance winner to next match
        elif match.next_match_id:
            match.advance_winner_to_next_match()
    
    # Update scheduling info
    if 'court' in request.form:
        match.court = request.form.get('court')
    
    if 'scheduled_time' in request.form:
        scheduled_time = request.form.get('scheduled_time')
        if scheduled_time:
            match.scheduled_time = datetime.strptime(scheduled_time, '%Y-%m-%dT%H:%M')
    
    db.session.commit()
    flash('Match updated successfully.', 'success')
    
    # Redirect back to match detail
    return redirect(url_for('tournament.match_detail', id=id, match_id=match_id))

@bp.route('/<int:id>/calculate_placings/<int:category_id>', methods=['POST'])
@login_required
def calculate_placings(id, category_id):
    """Calculate final placings for a category"""
    # Ensure the current user is the tournament organizer
    tournament = Tournament.query.get_or_404(id)
    if tournament.organizer_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to manage this tournament.', 'danger')
        return redirect(url_for('main.tournament_detail', id=id))
    
    # Make sure tournament is completed
    if tournament.status != TournamentStatus.COMPLETED:
        flash('Tournament must be completed to calculate placings.', 'warning')
        return redirect(url_for('tournament.admin.manage_category', id=id, category_id=category_id))
    
    # Calculate placings using our service
    placings = PlacingService.get_placings(category_id)
    
    flash(f'Calculated {len(placings)} placings for this category.', 'success')
    return redirect(url_for('tournament.results', id=id, category=category_id))



# @bp.route('/tournament/create', methods=['GET', 'POST'])
# @login_required
# @organizer_required
# def create_tournament():
#     form = TournamentForm()
    
#     if form.validate_on_submit():
#         tournament = Tournament(
#             name=form.name.data,
#             organizer_id=current_user.id,
#             location=form.location.data,
#             description=form.description.data,
#             start_date=form.start_date.data,
#             end_date=form.end_date.data,
#             registration_deadline=form.registration_deadline.data,
#             tier=TournamentTier[form.tier.data],
#             format=TournamentFormat[form.format.data],
#             status=TournamentStatus[form.status.data],
#             prize_pool=form.prize_pool.data
#         )
        
#         tournament.registration_fee = form.registration_fee.data

#         # Handle logo upload
#         if form.logo.data:
#             tournament.logo = save_picture(form.logo.data, 'tournament_logos')
        
#         # Handle banner upload
#         if form.banner.data:
#             tournament.banner = save_picture(form.banner.data, 'tournament_banners')
        
#         db.session.add(tournament)
#         db.session.commit()
        
#         flash('Tournament created successfully!', 'success')
#         return redirect(url_for('organizer.tournament_detail', id=tournament.id))
    
#     return render_template('organizer/create_tournament.html',
#                            title='Create Tournament',
#                            form=form)

@bp.route('/tournament/<int:id>')
@login_required
@organizer_required
def tournament_detail(id):
    tournament = Tournament.query.get_or_404(id)
    
    # Check if this tournament belongs to the current user
    if tournament.organizer_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to view this tournament.', 'danger')
        return redirect(url_for('organizer.dashboard'))
    
    # Get categories for this tournament
    categories = tournament.categories.all()
    
    # Get registrations by category
    registrations = {}
    registration_counts = {}
    for category in categories:
        registrations[category.id] = Registration.query.filter_by(category_id=category.id).all()
        
        # Count registrations and payment status
        registration_counts[category.id] = len(registrations[category.id])
    
    return render_template('organizer/tournament_detail.html',
                           title=f'Manage: {tournament.name}',
                           tournament=tournament,
                           categories=categories,
                           registrations=registrations,
                           registration_counts=registration_counts)

def string_to_tournament_format(format_string):
    """Convert a format string to the corresponding TournamentFormat enum"""
    for format_enum in TournamentFormat:
        if format_enum.value == format_string:
            return format_enum
    # If no match is found, return a default or raise an error
    return TournamentFormat.SINGLE_ELIMINATION  # Default value

@bp.route('/tournament/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@organizer_required
def edit_tournament(id):
    # Get tournament or return 404
    tournament = Tournament.query.get_or_404(id)
    
    # Check if current user is the organizer or an admin
    if tournament.organizer_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to edit this tournament.', 'danger')
        return redirect(url_for('organizer.tournament_detail', id=tournament.id))
    
    # Get all categories for this tournament
    categories = tournament.categories.order_by(TournamentCategory.display_order).all()
    
    form = TournamentForm()


    if request.method == 'POST':
        # Handle form submission
        if form.validate_on_submit():

            # Update tournament details
            form.populate_obj(tournament)
            
            # Convert string values to enums properly
            tournament.tier = TournamentTier[form.tier.data]
            tournament.format = TournamentFormat[form.format.data]
            tournament.status = TournamentStatus[form.status.data]

            print('post')
            print(tournament.tier)
            print(tournament.format)
            print(tournament.status)

            # Handle logo upload
            if form.logo.data:
                tournament.logo = save_picture(form.logo.data, 'tournament_logos')
            
            # Handle banner upload
            if form.banner.data:
                tournament.banner = save_picture(form.banner.data, 'tournament_banners')
            
            # Handle payment QR code upload
            if form.payment_qr_code.data:
                tournament.payment_qr_code = save_picture(form.payment_qr_code.data, 'payment_qr_codes')
            
            # Handle door gifts image upload
            if form.door_gifts_image.data:
                tournament.door_gifts_image = save_picture(form.door_gifts_image.data, 'door_gifts_images')
            
            # Save changes to the database
            db.session.commit()
            
            flash('Tournament details updated successfully!', 'success')
            return redirect(url_for('organizer.edit_categories', id=tournament.id))

        else:
            flash(f"Field {field} has errors: {errors}", 'danger')
            return redirect(url_for('organizer.edit_tournament', id=tournament.id))           
    
    # For GET requests, populate form with existing data

    if request.method == 'GET' or not form.validate_on_submit():
        # Initialize the form
        form.process(obj=tournament)

        if tournament.tier:
            form.tier.data = tournament.tier.name 
        if tournament.format:
            form.format.data = tournament.format.name  
        if tournament.status:
            form.status.data = tournament.status.name  

        return render_template(
            'organizer/edit_tournament.html',
            title=f'Edit Tournament - {tournament.name}',
            tournament=tournament,
            categories=categories,
            form=form
        )

@bp.route('/tournament/<int:id>/edit/categories', methods=['GET', 'POST'])
@login_required
@organizer_required
def edit_categories(id):
    # Get tournament or return 404
    tournament = Tournament.query.get_or_404(id)
    
    # Check if current user is the organizer or an admin
    if tournament.organizer_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to edit this tournament.', 'danger')
        return redirect(url_for('organizer.tournament_detail', id=tournament.id))
    
    # Get all categories for this tournament
    categories = tournament.categories.order_by(TournamentCategory.display_order).all()
    
    # Handle form submission
    if request.method == 'POST':
        # Process category updates
        updated_categories = []
        for category_id in request.form.getlist('category_id'):
            category = TournamentCategory.query.get(category_id)
            if category and category.tournament_id == tournament.id:
                # Update category details
                category.name = request.form.get(f'name_{category_id}')
                category.category_type = CategoryType(request.form.get(f'category_type_{category_id}'))
                category.max_participants = int(request.form.get(f'max_participants_{category_id}', 0))
                category.points_awarded = int(request.form.get(f'points_awarded_{category_id}', 0))
                category.format = TournamentFormat(request.form.get(f'format_{category_id}'))
                category.registration_fee = float(request.form.get(f'registration_fee_{category_id}', 0))
                category.description = request.form.get(f'description_{category_id}', '')
                category.display_order = int(request.form.get(f'display_order_{category_id}', 999))
                category.prize_percentage = float(request.form.get(f'prize_percentage_{category_id}', 0))
                category.prize_money = float(request.form.get(f'prize_money_{category_id}', 0))
                
                # Optional fields
                min_dupr = request.form.get(f'min_dupr_rating_{category_id}', '')
                max_dupr = request.form.get(f'max_dupr_rating_{category_id}', '')
                min_age = request.form.get(f'min_age_{category_id}', '')
                max_age = request.form.get(f'max_age_{category_id}', '')
                
                category.min_dupr_rating = float(min_dupr) if min_dupr else None
                category.max_dupr_rating = float(max_dupr) if max_dupr else None
                category.min_age = int(min_age) if min_age else None
                category.max_age = int(max_age) if max_age else None
                category.gender_restriction = request.form.get(f'gender_restriction_{category_id}', None)
                
                # Add to list of updated categories
                updated_categories.append(category)
        
        # Process new categories
        new_category_names = request.form.getlist('new_category_name')
        for i, name in enumerate(new_category_names):
            if name.strip():  # Only process if name is not empty
                new_cat = TournamentCategory(
                    tournament_id=tournament.id,
                    name=name,
                    category_type=CategoryType(request.form.getlist('new_category_type')[i]),
                    max_participants=int(request.form.getlist('new_max_participants')[i] or 0),
                    points_awarded=int(request.form.getlist('new_points_awarded')[i] or 0),
                    format=TournamentFormat(request.form.getlist('new_format')[i]),
                    registration_fee=float(request.form.getlist('new_registration_fee')[i] or 0),
                    description=request.form.getlist('new_description')[i] or '',
                    display_order=int(request.form.getlist('new_display_order')[i] or 999),
                    prize_percentage=float(request.form.getlist('new_prize_percentage')[i] or 0),
                    prize_money=float(request.form.getlist('new_prize_money')[i] or 0)
                )
                
                # Optional fields
                min_dupr = request.form.getlist('new_min_dupr_rating')[i]
                max_dupr = request.form.getlist('new_max_dupr_rating')[i]
                min_age = request.form.getlist('new_min_age')[i]
                max_age = request.form.getlist('new_max_age')[i]
                
                new_cat.min_dupr_rating = float(min_dupr) if min_dupr else None
                new_cat.max_dupr_rating = float(max_dupr) if max_dupr else None
                new_cat.min_age = int(min_age) if min_age else None
                new_cat.max_age = int(max_age) if max_age else None
                new_cat.gender_restriction = request.form.getlist('new_gender_restriction')[i] or None
                
                db.session.add(new_cat)
        
        # Process category deletions
        for category_id in request.form.getlist('delete_category'):
            category = TournamentCategory.query.get(category_id)
            if category and category.tournament_id == tournament.id:
                # Check if registrations exist for this category
                if category.registrations.count() > 0:
                    flash(f'Cannot delete category "{category.name}" because it has registrations.', 'warning')
                else:
                    db.session.delete(category)
        
        # Save changes
        db.session.commit()
        
        # Recalculate prize distribution
        for category in updated_categories:
            category.calculate_prize_values()
        
        # Update tournament totals
        tournament.total_cash_prize = sum(cat.prize_money for cat in tournament.categories)
        tournament.total_prize_value = sum(cat.total_prize_value for cat in tournament.categories)
        db.session.commit()
        
        flash('Tournament categories updated successfully!', 'success')
        return redirect(url_for('organizer.edit_prizes', id=tournament.id))
    
    # For GET requests, prepare the form
    return render_template(
        'organizer/edit_categories.html',
        title=f'Edit Categories - {tournament.name}',
        tournament=tournament,
        categories=categories,
        category_types=[(ct.value, ct.value) for ct in CategoryType],
        tournament_formats=[(tf.value, tf.value) for tf in TournamentFormat]
    )

@bp.route('/tournament/<int:id>/edit/prizes', methods=['GET', 'POST'])
@login_required
@organizer_required
def edit_prizes(id):
    # Get tournament or return 404
    tournament = Tournament.query.get_or_404(id)
    
    # Check if current user is the organizer or an admin
    if tournament.organizer_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to edit this tournament.', 'danger')
        return redirect(url_for('organizer.tournament_detail', id=tournament.id))
    
    # Get all categories for this tournament
    categories = tournament.categories.order_by(TournamentCategory.display_order).all()
    
    # Handle form submission
    if request.method == 'POST':
        # Process prize updates for each category
        for category in categories:
            # Get all prizes for this category
            prizes = Prize.query.filter_by(category_id=category.id).all()
            
            # Update existing prizes
            for prize in prizes:
                prize_id = str(prize.id)
                if f'prize_type_{prize_id}' in request.form:
                    prize.prize_type = PrizeType(request.form.get(f'prize_type_{prize_id}'))
                    prize.placement = request.form.get(f'placement_{prize_id}')
                    
                    # Set fields based on prize type
                    if prize.prize_type == PrizeType.CASH:
                        prize.cash_amount = float(request.form.get(f'cash_amount_{prize_id}', 0))
                    elif prize.prize_type in [PrizeType.MERCHANDISE]:
                        prize.title = request.form.get(f'title_{prize_id}', '')
                        prize.description = request.form.get(f'description_{prize_id}', '')
                        prize.monetary_value = float(request.form.get(f'monetary_value_{prize_id}', 0))
                        prize.quantity = int(request.form.get(f'quantity_{prize_id}', 1))
            
            # Process new prizes
            new_prize_placements = request.form.getlist(f'new_placement_{category.id}')
            for i, placement in enumerate(new_prize_placements):
                if placement.strip():  # Only process if placement is not empty
                    prize_type = PrizeType(request.form.getlist(f'new_prize_type_{category.id}')[i])
                    new_prize = Prize(
                        category_id=category.id,
                        placement=placement,
                        prize_type=prize_type
                    )
                    
                    # Set fields based on prize type
                    if prize_type == PrizeType.CASH:
                        new_prize.cash_amount = float(request.form.getlist(f'new_cash_amount_{category.id}')[i] or 0)
                    elif prize_type in [PrizeType.MERCHANDISE]:
                        new_prize.title = request.form.getlist(f'new_title_{category.id}')[i] or ''
                        new_prize.description = request.form.getlist(f'new_description_{category.id}')[i] or ''
                        new_prize.monetary_value = float(request.form.getlist(f'new_monetary_value_{category.id}')[i] or 0)
                        new_prize.quantity = int(request.form.getlist(f'new_quantity_{category.id}')[i] or 1)
                    
                    db.session.add(new_prize)
            
            # Process prize deletions
            for prize_id in request.form.getlist(f'delete_prize_{category.id}'):
                prize = Prize.query.get(prize_id)
                if prize and prize.category_id == category.id:
                    db.session.delete(prize)
        
        # Save changes
        db.session.commit()
        
        # Update category flags and totals
        for category in categories:
            # Update flags
            category.has_merchandise = Prize.query.filter(
                Prize.category_id == category.id,
                Prize.prize_type.in_([PrizeType.MERCHANDISE])
            ).count() > 0
            
            # Update total prize values
            category.prize_money = Prize.query.filter_by(
                category_id=category.id,
                prize_type=PrizeType.CASH
            ).with_entities(db.func.sum(Prize.cash_amount)).scalar() or 0
            
            merchandise_value = db.session.query(
                db.func.sum(Prize.monetary_value * Prize.quantity)
            ).filter(
                Prize.category_id == category.id,
                Prize.prize_type.in_([PrizeType.MERCHANDISE])
            ).scalar() or 0
            
            category.total_prize_value = category.prize_money + merchandise_value
        
        # Update tournament totals
        tournament.total_cash_prize = sum(cat.prize_money for cat in categories)
        tournament.total_prize_value = sum(cat.total_prize_value for cat in categories)
        
        db.session.commit()
        
        flash('Tournament prizes updated successfully!', 'success')
        return redirect(url_for('organizer.tournament_detail', id=tournament.id))
    
    # For GET requests, gather prize data
    prize_data = {}
    for category in categories:
        prize_data[category.id] = Prize.query.filter_by(category_id=category.id).all()
    
    return render_template(
        'organizer/edit_prizes.html',
        title=f'Edit Prizes - {tournament.name}',
        tournament=tournament,
        categories=categories,
        prize_data=prize_data,
        prize_types=[(pt.value, pt.name) for pt in PrizeType]
    )

# @bp.route('/tournament/<int:id>/category/<int:category_id>/manage')
# @login_required
# @organizer_required
# def manage_category(id, category_id):
#     tournament = Tournament.query.get_or_404(id)
#     category = TournamentCategory.query.get_or_404(category_id)
    
#     # Check if this tournament belongs to the current user
#     if tournament.organizer_id != current_user.id and not current_user.is_admin():
#         flash('You do not have permission to manage this tournament.', 'danger')
#         return redirect(url_for('organizer.dashboard'))
    
#     # Check if category belongs to this tournament
#     if category.tournament_id != id:
#         flash('Category not found in this tournament.', 'danger')
#         return redirect(url_for('organizer.tournament_detail', id=id))
    
#     # Get registrations for this category
#     registrations = Registration.query.filter_by(category_id=category_id).all()
    
#     # Get matches for this category
#     matches = Match.query.filter_by(category_id=category_id).order_by(Match.round.desc(), Match.match_order).all()
    
#     return render_template('organizer/manage_category.html',
#                            title=f'Manage {category.category_type.value}',
#                            tournament=tournament,
#                            category=category,
#                            registrations=registrations,
#                            matches=matches)

# @bp.route('/tournament/<int:id>/category/<int:category_id>/registrations')
# @login_required
# @organizer_required
# def manage_registrations(id, category_id):
#     tournament = Tournament.query.get_or_404(id)
#     category = TournamentCategory.query.get_or_404(category_id)
    
#     # Check if this tournament belongs to the current user
#     if tournament.organizer_id != current_user.id and not current_user.is_admin():
#         flash('You do not have permission to manage this tournament.', 'danger')
#         return redirect(url_for('organizer.dashboard'))
    
#     # Check if category belongs to this tournament
#     if category.tournament_id != id:
#         flash('Category not found in this tournament.', 'danger')
#         return redirect(url_for('organizer.tournament_detail', id=id))
    
#     # Get registrations for this category
#     registrations = Registration.query.filter_by(category_id=category_id).all()
    
#     return render_template('organizer/manage_registrations.html',
#                            title=f'Manage Registrations for {category.category_type.value}',
#                            tournament=tournament,
#                            category=category,
#                            registrations=registrations)

# @bp.route('/tournament/<int:id>/approve_registration/<int:registration_id>', methods=['POST'])
# @login_required
# @organizer_required
# def approve_registration(id, registration_id):
#     """Approve a tournament registration and verify payment"""
#     # Get tournament and registration
#     tournament = Tournament.query.get_or_404(id)
#     registration = Registration.query.get_or_404(registration_id)
    
#     # Ensure the registration belongs to this tournament
#     if registration.category.tournament_id != tournament.id:
#         flash('Invalid registration for this tournament.', 'danger')
#         return redirect(url_for('organizer.tournament_registrations', id=id))
    
#     # Verify organizer has permission
#     if tournament.organizer_id != current_user.id and not current_user.is_admin():
#         flash('You do not have permission to approve registrations for this tournament.', 'danger')
#         return redirect(url_for('organizer.dashboard'))
    
#     # Update registration status
#     registration.is_approved = True
#     registration.payment_status = 'paid'  # Mark as paid
#     registration.payment_verified = True
#     registration.payment_verified_at = datetime.utcnow()
#     registration.payment_verified_by = current_user.id
    
#     # If there's a payment date field, update it
#     if hasattr(registration, 'payment_date') and not registration.payment_date:
#         registration.payment_date = datetime.utcnow()
    
#     # Save changes
#     db.session.commit()
    
#     # Notify the players (could be implemented with email)
#     # Placeholder for email notification logic
    
#     flash(f'Registration for {registration.team_name} has been approved successfully.', 'success')
#     return redirect(url_for('organizer.tournament_registrations', id=id))

# @bp.route('/tournament/<int:id>/reject_registration/<int:registration_id>', methods=['POST'])
# @login_required
# @organizer_required
# def reject_registration(id, registration_id):
#     tournament = Tournament.query.get_or_404(id)
    
#     # Check if this tournament belongs to the current user
#     if tournament.organizer_id != current_user.id and not current_user.is_admin():
#         flash('You do not have permission to manage this tournament.', 'danger')
#         return redirect(url_for('organizer.dashboard'))
    
#     registration = Registration.query.get_or_404(registration_id)
    
#     # Check if registration belongs to this category
#     if registration.category_id != category_id:
#         flash('Registration not found in this category.', 'danger')
#         return redirect(url_for('organizer.manage_registrations', id=id, category_id=category_id))
    
#     # Delete registration
#     db.session.delete(registration)
#     db.session.commit()
    
#     flash('Registration rejected and removed.', 'success')
#     return redirect(url_for('organizer.manage_registrations', id=id, category_id=category_id))

# @bp.route('/tournament/<int:id>/category/<int:category_id>/update_seed/<int:registration_id>', methods=['POST'])
# @login_required
# @organizer_required
# def update_seed(id, category_id, registration_id):
#     tournament = Tournament.query.get_or_404(id)
    
#     # Check if this tournament belongs to the current user
#     if tournament.organizer_id != current_user.id and not current_user.is_admin():
#         flash('You do not have permission to manage this tournament.', 'danger')
#         return redirect(url_for('organizer.dashboard'))
    
#     registration = Registration.query.get_or_404(registration_id)
    
#     # Check if registration belongs to this category
#     if registration.category_id != category_id:
#         flash('Registration not found in this category.', 'danger')
#         return redirect(url_for('organizer.manage_registrations', id=id, category_id=category_id))
    
#     form = SeedingForm()
    
#     if form.validate_on_submit():
#         registration.seed = form.seed.data
#         db.session.commit()
        
#         flash('Seed updated successfully!', 'success')
    
#     return redirect(url_for('organizer.manage_registrations', id=id, category_id=category_id))

# @bp.route('/tournament/<int:id>/category/<int:category_id>/generate_bracket', methods=['GET', 'POST'])
# @login_required
# @organizer_required
# def generate_bracket(id, category_id):
#     tournament = Tournament.query.get_or_404(id)
#     category = TournamentCategory.query.get_or_404(category_id)
    
#     # Check if this tournament belongs to the current user
#     if tournament.organizer_id != current_user.id and not current_user.is_admin():
#         flash('You do not have permission to manage this tournament.', 'danger')
#         return redirect(url_for('organizer.dashboard'))
    
#     # Check if category belongs to this tournament
#     if category.tournament_id != id:
#         flash('Category not found in this tournament.', 'danger')
#         return redirect(url_for('organizer.tournament_detail', id=id))
    
#     form = BracketGenerationForm()
#     form.category_id.data = category_id
    
#     if form.validate_on_submit():
#         # Get approved registrations
#         registrations = Registration.query.filter_by(
#             category_id=category_id,
#             is_approved=True
#         ).all()
        
#         # Check if there are enough participants
#         if len(registrations) < 2:
#             flash('Need at least 2 approved participants to generate a bracket.', 'warning')
#             return redirect(url_for('organizer.manage_category', id=id, category_id=category_id))
        
#         # Delete existing matches for this category
#         Match.query.filter_by(category_id=category_id).delete()
#         db.session.commit()
        
#         # Generate bracket based on tournament format
#         if tournament.format == TournamentFormat.SINGLE_ELIMINATION:
#             generate_single_elimination_bracket(category, registrations, form.use_seeding.data, form.third_place_match.data)
#         elif tournament.format == TournamentFormat.DOUBLE_ELIMINATION:
#             # This would be more complex to implement
#             flash('Double elimination bracket generation not yet implemented.', 'warning')
#         elif tournament.format == TournamentFormat.ROUND_ROBIN:
#             generate_round_robin(category, registrations)
#         elif tournament.format == TournamentFormat.GROUP_KNOCKOUT:
#             # This would require group stage setup first
#             flash('Group stage + knockout format not yet implemented.', 'warning')
        
#         flash('Bracket generated successfully!', 'success')
#         return redirect(url_for('organizer.manage_category', id=id, category_id=category_id))
    
#     return render_template('organizer/generate_bracket.html',
#                            title=f'Generate Bracket for {category.category_type.value}',
#                            tournament=tournament,
#                            category=category,
#                            form=form)

# def generate_single_elimination_bracket(category, registrations, use_seeding=True, third_place_match=False):
#     # Get the number of participants and calculate bracket size
#     num_participants = len(registrations)
#     bracket_size = 1
#     while bracket_size < num_participants:
#         bracket_size *= 2
    
#     # Initialize players list - will contain player IDs or None for byes
#     players = []
    
#     if use_seeding:
#         # Sort registrations by seed (if available)
#         registrations.sort(key=lambda r: r.seed if r.seed else 999)
        
#         # Create a properly seeded bracket (this is a simplified version)
#         # In a real implementation, you'd use a proper seeding algorithm
#         for reg in registrations:
#             players.append(reg.player_id)
        
#         # Add byes for empty spots
#         players.extend([None] * (bracket_size - len(players)))
#     else:
#         # Randomize the order
#         player_ids = [reg.player_id for reg in registrations]
#         random.shuffle(player_ids)
#         players = player_ids
        
#         # Add byes for empty spots
#         players.extend([None] * (bracket_size - len(players)))
    
#     # Calculate number of rounds
#     num_rounds = int(math.log2(bracket_size))
    
#     # Create matches for each round
#     matches = []
#     match_count_by_round = {}
    
#     # Create first round matches
#     for i in range(0, bracket_size, 2):
#         player1_id = players[i]
#         player2_id = players[i + 1]
        
#         # If one player has a bye, they advance automatically
#         if player1_id is None and player2_id is not None:
#             # Player 2 advances
#             next_round_match_order = i // 4
#             next_round_player_position = (i // 2) % 2  # 0 for player1, 1 for player2
            
#             # Create new match
#             match = Match(
#                 category_id=category.id,
#                 round=num_rounds,
#                 match_order=i // 2,
#                 player1_id=None,
#                 player2_id=player2_id
#             )
#             db.session.add(match)
#             matches.append(match)
            
#         elif player1_id is not None and player2_id is None:
#             # Player 1 advances
#             next_round_match_order = i // 4
#             next_round_player_position = (i // 2) % 2  # 0 for player1, 1 for player2
            
#             # Create new match
#             match = Match(
#                 category_id=category.id,
#                 round=num_rounds,
#                 match_order=i // 2,
#                 player1_id=player1_id,
#                 player2_id=None
#             )
#             db.session.add(match)
#             matches.append(match)
            
#         elif player1_id is not None and player2_id is not None:
#             # Regular match
#             match = Match(
#                 category_id=category.id,
#                 round=num_rounds,
#                 match_order=i // 2,
#                 player1_id=player1_id,
#                 player2_id=player2_id
#             )
#             db.session.add(match)
#             matches.append(match)
        
#         # Skip if both players are None (empty match)
    
#     # Create matches for subsequent rounds
#     for round_num in range(num_rounds - 1, 0, -1):
#         matches_in_round = 2 ** (round_num - 1)
#         for i in range(matches_in_round):
#             match = Match(
#                 category_id=category.id,
#                 round=round_num,
#                 match_order=i
#             )
#             db.session.add(match)
#             matches.append(match)
    
#     # Create third place match if requested
#     if third_place_match:
#         match = Match(
#             category_id=category.id,
#             round=1.5,  # Use a special round number for third place match
#             match_order=0
#         )
#         db.session.add(match)
#         matches.append(match)
    
#     db.session.commit()
    
#     # Link matches to set up advancement path
#     for match in matches:
#         if match.round > 1:
#             # Find the next match in the bracket
#             next_round = match.round - 1
#             next_match_order = match.match_order // 2
            
#             next_match = next((m for m in matches if m.round == next_round and m.match_order == next_match_order), None)
            
#             if next_match:
#                 match.next_match_id = next_match.id
    
#     db.session.commit()

# def generate_round_robin(category, registrations):
#     # Get all player IDs
#     player_ids = [reg.player_id for reg in registrations]
#     num_players = len(player_ids)
    
#     # Make sure we have an even number of players
#     if num_players % 2 == 1:
#         player_ids.append(None)  # Add a "bye" player
#         num_players += 1
    
#     # Calculate number of rounds and matches per round
#     num_rounds = num_players - 1
#     matches_per_round = num_players // 2
    
#     # Create schedule using circle method
#     # Keep one player fixed and rotate the rest
#     fixed_player = player_ids[0]
#     rotating_players = player_ids[1:]
    
#     round_num = 1
#     for _ in range(num_rounds):
#         # Create matches for this round
#         for i in range(matches_per_round):
#             player1_id = None
#             player2_id = None
            
#             if i == 0:
#                 player1_id = fixed_player
#                 player2_id = rotating_players[0]
#             else:
#                 player1_id = rotating_players[i]
#                 player2_id = rotating_players[num_players - 2 - i]
            
#             # Skip matches involving the "bye" player
#             if player1_id is not None and player2_id is not None:
#                 match = Match(
#                     category_id=category.id,
#                     round=round_num,
#                     match_order=i,
#                     player1_id=player1_id,
#                     player2_id=player2_id
#                 )
#                 db.session.add(match)
        
#         # Rotate players for next round
#         rotating_players.insert(0, rotating_players.pop())
#         round_num += 1
    
#     db.session.commit()

# @bp.route('/tournament/<int:id>/category/<int:category_id>/match/<int:match_id>/edit', methods=['GET', 'POST'])
# @login_required
# @organizer_required
# def edit_match(id, category_id, match_id):
#     tournament = Tournament.query.get_or_404(id)
#     category = TournamentCategory.query.get_or_404(category_id)
#     match = Match.query.get_or_404(match_id)
    
#     # Check if this tournament belongs to the current user
#     if tournament.organizer_id != current_user.id and not current_user.is_admin():
#         flash('You do not have permission to manage this tournament.', 'danger')
#         return redirect(url_for('organizer.dashboard'))
    
#     # Check if match belongs to this category
#     if match.category_id != category_id:
#         flash('Match not found in this category.', 'danger')
#         return redirect(url_for('organizer.manage_category', id=id, category_id=category_id))
    
#     form = MatchForm(obj=match)
    
#     # Get all registered players for this category
#     registrations = Registration.query.filter_by(category_id=category_id, is_approved=True).all()
#     players = [(0, 'TBD')]
#     for reg in registrations:
#         player = PlayerProfile.query.get(reg.player_id)
#         if player:
#             players.append((player.id, player.full_name))
    
#     form.player1_id.choices = players
#     form.player2_id.choices = players
#     form.player1_partner_id.choices = players
#     form.player2_partner_id.choices = players
    
#     if form.validate_on_submit():
#         match.court = form.court.data
        
#         # Combine date and time
#         if form.scheduled_time.data and form.scheduled_time_hour.data:
#             match.scheduled_time = datetime.combine(
#                 form.scheduled_time.data,
#                 form.scheduled_time_hour.data
#             )
        
#         match.player1_id = form.player1_id.data if form.player1_id.data != 0 else None
#         match.player2_id = form.player2_id.data if form.player2_id.data != 0 else None
        
#         # Handle doubles partners
#         if category.category_type in [CategoryType.MENS_DOUBLES, CategoryType.WOMENS_DOUBLES, CategoryType.MIXED_DOUBLES]:
#             match.player1_partner_id = form.player1_partner_id.data if form.player1_partner_id.data != 0 else None
#             match.player2_partner_id = form.player2_partner_id.data if form.player2_partner_id.data != 0 else None
        
#         db.session.commit()
        
#         flash('Match updated successfully!', 'success')
#         return redirect(url_for('organizer.manage_category', id=id, category_id=category_id))
    
#     # Pre-populate form
#     if match.player1_id:
#         form.player1_id.data = match.player1_id
#     if match.player2_id:
#         form.player2_id.data = match.player2_id
#     if match.player1_partner_id:
#         form.player1_partner_id.data = match.player1_partner_id
#     if match.player2_partner_id:
#         form.player2_partner_id.data = match.player2_partner_id
    
#     if match.scheduled_time:
#         form.scheduled_time.data = match.scheduled_time.date()
#         form.scheduled_time_hour.data = match.scheduled_time.time()
    
#     return render_template('organizer/edit_match.html',
#                            title='Edit Match',
#                            tournament=tournament,
#                            category=category,
#                            match=match,
#                            form=form)

# @bp.route('/tournament/<int:id>/category/<int:category_id>/match/<int:match_id>/score', methods=['GET', 'POST'])
# @login_required
# @organizer_required
# def edit_score(id, category_id, match_id):
#     tournament = Tournament.query.get_or_404(id)
#     category = TournamentCategory.query.get_or_404(category_id)
#     match = Match.query.get_or_404(match_id)
    
#     # Check if this tournament belongs to the current user
#     if tournament.organizer_id != current_user.id and not current_user.is_admin():
#         flash('You do not have permission to manage this tournament.', 'danger')
#         return redirect(url_for('organizer.dashboard'))
    
#     # Check if match belongs to this category
#     if match.category_id != category_id:
#         flash('Match not found in this category.', 'danger')
#         return redirect(url_for('organizer.manage_category', id=id, category_id=category_id))
    
#     form = ScoreForm()
    
#     if form.validate_on_submit():
#         # Check if this set already exists
#         score = MatchScore.query.filter_by(
#             match_id=match_id,
#             set_number=form.set_number.data
#         ).first()
        
#         if score:
#             # Update existing score
#             score.player1_score = form.player1_score.data
#             score.player2_score = form.player2_score.data
#         else:
#             # Create new score
#             score = MatchScore(
#                 match_id=match_id,
#                 set_number=form.set_number.data,
#                 player1_score=form.player1_score.data,
#                 player2_score=form.player2_score.data
#             )
#             db.session.add(score)
        
#         db.session.commit()
        
#         flash('Score updated successfully!', 'success')
#         return redirect(url_for('organizer.edit_score', id=id, category_id=category_id, match_id=match_id))
    
#     # Get existing scores
#     scores = MatchScore.query.filter_by(match_id=match_id).order_by(MatchScore.set_number).all()
    
#     return render_template('organizer/edit_score.html',
#                            title='Edit Match Score',
#                            tournament=tournament,
#                            category=category,
#                            match=match,
#                            form=form,
#                            scores=scores)

# @bp.route('/tournament/<int:id>/category/<int:category_id>/match/<int:match_id>/complete', methods=['POST'])
# @login_required
# @organizer_required
# def complete_match(id, category_id, match_id):
#     tournament = Tournament.query.get_or_404(id)
#     match = Match.query.get_or_404(match_id)
    
#     # Check if this tournament belongs to the current user
#     if tournament.organizer_id != current_user.id and not current_user.is_admin():
#         flash('You do not have permission to manage this tournament.', 'danger')
#         return redirect(url_for('organizer.dashboard'))
    
#     form = CompleteMatchForm()
    
#     if form.validate_on_submit():
#         match_id = form.match_id.data
#         winner_id = form.winner_id.data
#         completed = form.completed.data
        
#         match = Match.query.get_or_404(match_id)
        
#         # Set winner and loser
#         match.winner_id = winner_id
#         if winner_id == match.player1_id:
#             match.loser_id = match.player2_id
#         else:
#             match.loser_id = match.player1_id
        
#         match.completed = completed
        
#         # If match is completed and has a next match, advance the winner
#         if completed and match.next_match_id:
#             next_match = Match.query.get(match.next_match_id)
#             if next_match:
#                 # Determine if winner should be player1 or player2 in next match
#                 if match.match_order % 2 == 0:
#                     next_match.player1_id = winner_id
#                     if match.player1_partner_id and match.player1_id == winner_id:
#                         next_match.player1_partner_id = match.player1_partner_id
#                     elif match.player2_partner_id and match.player2_id == winner_id:
#                         next_match.player1_partner_id = match.player2_partner_id
#                 else:
#                     next_match.player2_id = winner_id
#                     if match.player1_partner_id and match.player1_id == winner_id:
#                         next_match.player2_partner_id = match.player1_partner_id
#                     elif match.player2_partner_id and match.player2_id == winner_id:
#                         next_match.player2_partner_id = match.player2_partner_id
        
#         db.session.commit()
        
#         flash('Match completed successfully!', 'success')
#         return redirect(url_for('organizer.manage_category', id=id, category_id=category_id))
    
#     return redirect(url_for('organizer.manage_category', id=id, category_id=category_id))

# @bp.route('/tournament/<int:id>/category/<int:category_id>/finalize', methods=['POST'])
# @login_required
# @organizer_required
# def finalize_category(id, category_id):
#     tournament = Tournament.query.get_or_404(id)
#     category = TournamentCategory.query.get_or_404(category_id)
    
#     # Check if this tournament belongs to the current user
#     if tournament.organizer_id != current_user.id and not current_user.is_admin():
#         flash('You do not have permission to manage this tournament.', 'danger')
#         return redirect(url_for('organizer.dashboard'))
    
#     # Check if all matches are completed
#     incomplete_matches = Match.query.filter_by(category_id=category_id, completed=False).count()
#     if incomplete_matches > 0:
#         flash(f'Cannot finalize category with {incomplete_matches} incomplete matches.', 'warning')
#         return redirect(url_for('organizer.manage_category', id=id, category_id=category_id))
    
#     # Get the final match (round 1)
#     final_match = Match.query.filter_by(category_id=category_id, round=1).first()
    
#     if not final_match or not final_match.winner_id:
#         flash('Cannot finalize category without a winner.', 'warning')
#         return redirect(url_for('organizer.manage_category', id=id, category_id=category_id))
    
#     # Award points to players based on their placement
#     winner_profile = PlayerProfile.query.get(final_match.winner_id)
#     runner_up_profile = PlayerProfile.query.get(final_match.loser_id)
    
#     # Get point values from config
#     points_distribution = current_app.config['POINTS_DISTRIBUTION']
#     total_points = category.points_awarded
    
#     # Award points based on category type
#     if category.category_type == CategoryType.MENS_SINGLES:
#         if winner_profile:
#             winner_profile.mens_singles_points += int(total_points * points_distribution[1] / 100)
#         if runner_up_profile:
#             runner_up_profile.mens_singles_points += int(total_points * points_distribution[2] / 100)
    
#     elif category.category_type == CategoryType.WOMENS_SINGLES:
#         if winner_profile:
#             winner_profile.womens_singles_points += int(total_points * points_distribution[1] / 100)
#         if runner_up_profile:
#             runner_up_profile.womens_singles_points += int(total_points * points_distribution[2] / 100)
    
#     elif category.category_type == CategoryType.MENS_DOUBLES:
#         if winner_profile:
#             winner_profile.mens_doubles_points += int(total_points * points_distribution[1] / 100)
#         if runner_up_profile:
#             runner_up_profile.mens_doubles_points += int(total_points * points_distribution[2] / 100)
        
#         # Award points to partners as well
#         if final_match.player1_partner_id and final_match.player1_id == final_match.winner_id:
#             partner_profile = PlayerProfile.query.get(final_match.player1_partner_id)
#             if partner_profile:
#                 partner_profile.mens_doubles_points += int(total_points * points_distribution[1] / 100)
        
#         if final_match.player2_partner_id and final_match.player2_id == final_match.winner_id:
#             partner_profile = PlayerProfile.query.get(final_match.player2_partner_id)
#             if partner_profile:
#                 partner_profile.mens_doubles_points += int(total_points * points_distribution[1] / 100)
        
#         if final_match.player1_partner_id and final_match.player1_id == final_match.loser_id:
#             partner_profile = PlayerProfile.query.get(final_match.player1_partner_id)
#             if partner_profile:
#                 partner_profile.mens_doubles_points += int(total_points * points_distribution[2] / 100)
        
#         if final_match.player2_partner_id and final_match.player2_id == final_match.loser_id:
#             partner_profile = PlayerProfile.query.get(final_match.player2_partner_id)
#             if partner_profile:
#                 partner_profile.mens_doubles_points += int(total_points * points_distribution[2] / 100)
    
#     elif category.category_type == CategoryType.WOMENS_DOUBLES:
#         if winner_profile:
#             winner_profile.womens_doubles_points += int(total_points * points_distribution[1] / 100)
#         if runner_up_profile:
#             runner_up_profile.womens_doubles_points += int(total_points * points_distribution[2] / 100)
        
#         # Award points to partners as well
#         if final_match.player1_partner_id and final_match.player1_id == final_match.winner_id:
#             partner_profile = PlayerProfile.query.get(final_match.player1_partner_id)
#             if partner_profile:
#                 partner_profile.womens_doubles_points += int(total_points * points_distribution[1] / 100)
        
#         if final_match.player2_partner_id and final_match.player2_id == final_match.winner_id:
#             partner_profile = PlayerProfile.query.get(final_match.player2_partner_id)
#             if partner_profile:
#                 partner_profile.womens_doubles_points += int(total_points * points_distribution[1] / 100)
        
#         if final_match.player1_partner_id and final_match.player1_id == final_match.loser_id:
#             partner_profile = PlayerProfile.query.get(final_match.player1_partner_id)
#             if partner_profile:
#                 partner_profile.womens_doubles_points += int(total_points * points_distribution[2] / 100)
        
#         if final_match.player2_partner_id and final_match.player2_id == final_match.loser_id:
#             partner_profile = PlayerProfile.query.get(final_match.player2_partner_id)
#             if partner_profile:
#                 partner_profile.womens_doubles_points += int(total_points * points_distribution[2] / 100)
    
#     elif category.category_type == CategoryType.MIXED_DOUBLES:
#         if winner_profile:
#             winner_profile.mixed_doubles_points += int(total_points * points_distribution[1] / 100)
#         if runner_up_profile:
#             runner_up_profile.mixed_doubles_points += int(total_points * points_distribution[2] / 100)
        
#         # Award points to partners as well
#         if final_match.player1_partner_id and final_match.player1_id == final_match.winner_id:
#             partner_profile = PlayerProfile.query.get(final_match.player1_partner_id)
#             if partner_profile:
#                 partner_profile.mixed_doubles_points += int(total_points * points_distribution[1] / 100)
        
#         if final_match.player2_partner_id and final_match.player2_id == final_match.winner_id:
#             partner_profile = PlayerProfile.query.get(final_match.player2_partner_id)
#             if partner_profile:
#                 partner_profile.mixed_doubles_points += int(total_points * points_distribution[1] / 100)
        
#         if final_match.player1_partner_id and final_match.player1_id == final_match.loser_id:
#             partner_profile = PlayerProfile.query.get(final_match.player1_partner_id)
#             if partner_profile:
#                 partner_profile.mixed_doubles_points += int(total_points * points_distribution[2] / 100)
        
#         if final_match.player2_partner_id and final_match.player2_id == final_match.loser_id:
#             partner_profile = PlayerProfile.query.get(final_match.player2_partner_id)
#             if partner_profile:
#                 partner_profile.mixed_doubles_points += int(total_points * points_distribution[2] / 100)
    
#     # Award points to semifinalists (3rd and 4th place)
#     semifinal_matches = Match.query.filter_by(category_id=category_id, round=2).all()
    
#     for semifinal in semifinal_matches:
#         if semifinal.loser_id:
#             semifinalist_profile = PlayerProfile.query.get(semifinal.loser_id)
#             if semifinalist_profile:
#                 # Award points based on category
#                 if category.category_type == CategoryType.MENS_SINGLES:
#                     semifinalist_profile.mens_singles_points += int(total_points * points_distribution[3] / 100)
#                 elif category.category_type == CategoryType.WOMENS_SINGLES:
#                     semifinalist_profile.womens_singles_points += int(total_points * points_distribution[3] / 100)
#                 elif category.category_type == CategoryType.MENS_DOUBLES:
#                     semifinalist_profile.mens_doubles_points += int(total_points * points_distribution[3] / 100)
                    
#                     # Award points to partner
#                     if semifinal.player1_partner_id and semifinal.player1_id == semifinal.loser_id:
#                         partner_profile = PlayerProfile.query.get(semifinal.player1_partner_id)
#                         if partner_profile:
#                             partner_profile.mens_doubles_points += int(total_points * points_distribution[3] / 100)
                    
#                     if semifinal.player2_partner_id and semifinal.player2_id == semifinal.loser_id:
#                         partner_profile = PlayerProfile.query.get(semifinal.player2_partner_id)
#                         if partner_profile:
#                             partner_profile.mens_doubles_points += int(total_points * points_distribution[3] / 100)
                    
#                 elif category.category_type == CategoryType.WOMENS_DOUBLES:
#                     semifinalist_profile.womens_doubles_points += int(total_points * points_distribution[3] / 100)
                    
#                     # Award points to partner
#                     if semifinal.player1_partner_id and semifinal.player1_id == semifinal.loser_id:
#                         partner_profile = PlayerProfile.query.get(semifinal.player1_partner_id)
#                         if partner_profile:
#                             partner_profile.womens_doubles_points += int(total_points * points_distribution[3] / 100)
                    
#                     if semifinal.player2_partner_id and semifinal.player2_id == semifinal.loser_id:
#                         partner_profile = PlayerProfile.query.get(semifinal.player2_partner_id)
#                         if partner_profile:
#                             partner_profile.womens_doubles_points += int(total_points * points_distribution[3] / 100)
                    
#                 elif category.category_type == CategoryType.MIXED_DOUBLES:
#                     semifinalist_profile.mixed_doubles_points += int(total_points * points_distribution[3] / 100)
                    
#                     # Award points to partner
#                     if semifinal.player1_partner_id and semifinal.player1_id == semifinal.loser_id:
#                         partner_profile = PlayerProfile.query.get(semifinal.player1_partner_id)
#                         if partner_profile:
#                             partner_profile.mixed_doubles_points += int(total_points * points_distribution[3] / 100)
                    
#                     if semifinal.player2_partner_id and semifinal.player2_id == semifinal.loser_id:
#                         partner_profile = PlayerProfile.query.get(semifinal.player2_partner_id)
#                         if partner_profile:
#                             partner_profile.mixed_doubles_points += int(total_points * points_distribution[3] / 100)
    
#     db.session.commit()
    
#     flash('Category finalized and points awarded to players!', 'success')
#     return redirect(url_for('organizer.manage_category', id=id, category_id=category_id))

# @bp.route('/tournament/<int:id>/finalize', methods=['POST'])
# @login_required
# @organizer_required
# def finalize_tournament(id):
#     tournament = Tournament.query.get_or_404(id)
    
#     # Check if this tournament belongs to the current user
#     if tournament.organizer_id != current_user.id and not current_user.is_admin():
#         flash('You do not have permission to manage this tournament.', 'danger')
#         return redirect(url_for('organizer.dashboard'))
    
#     # Check if all categories have been finalized
#     all_finalized = True
#     categories = tournament.categories.all()
    
#     for category in categories:
#         # Check if all matches are completed
#         incomplete_matches = Match.query.filter_by(category_id=category.id, completed=False).count()
#         if incomplete_matches > 0:
#             all_finalized = False
#             break
    
#     if not all_finalized:
#         flash('Cannot finalize tournament until all categories have been finalized.', 'warning')
#         return redirect(url_for('organizer.tournament_detail', id=id))
    
#     # Mark tournament as completed
#     tournament.status = TournamentStatus.COMPLETED
#     db.session.commit()
    
#     flash('Tournament finalized successfully!', 'success')
#     return redirect(url_for('organizer.tournament_detail', id=id))

# @bp.route('/tournament/<int:id>/export_results')
# @login_required
# @organizer_required
# def export_results(id):
#     tournament = Tournament.query.get_or_404(id)
    
#     # Check if this tournament belongs to the current user
#     if tournament.organizer_id != current_user.id and not current_user.is_admin():
#         flash('You do not have permission to manage this tournament.', 'danger')
#         return redirect(url_for('organizer.dashboard'))
    
#     # Prepare data for export
#     result_data = {
#         'tournament': {
#             'id': tournament.id,
#             'name': tournament.name,
#             'location': tournament.location,
#             'start_date': tournament.start_date.strftime('%Y-%m-%d'),
#             'end_date': tournament.end_date.strftime('%Y-%m-%d'),
#             'tier': tournament.tier.value,
#             'format': tournament.format.value,
#             'status': tournament.status.value,
#             'prize_pool': tournament.prize_pool
#         },
#         'categories': []
#     }
    
#     categories = tournament.categories.all()
#     for category in categories:
#         category_data = {
#             'id': category.id,
#             'type': category.category_type.value,
#             'points_awarded': category.points_awarded,
#             'winners': [],
#             'matches': []
#         }
        
#         # Get final match to determine winners
#         final_match = Match.query.filter_by(category_id=category.id, round=1).first()
#         if final_match and final_match.winner_id:
#             winner = PlayerProfile.query.get(final_match.winner_id)
#             runner_up = PlayerProfile.query.get(final_match.loser_id)
            
#             if winner:
#                 category_data['winners'].append({
#                     'place': 1,
#                     'player_id': winner.id,
#                     'player_name': winner.full_name,
#                     'country': winner.country
#                 })
            
#             if runner_up:
#                 category_data['winners'].append({
#                     'place': 2,
#                     'player_id': runner_up.id,
#                     'player_name': runner_up.full_name,
#                     'country': runner_up.country
#                 })
        
#         # Get completed matches
#         matches = Match.query.filter_by(category_id=category.id, completed=True).all()
#         for match in matches:
#             match_data = {
#                 'id': match.id,
#                 'round': match.round,
#                 'player1_id': match.player1_id,
#                 'player2_id': match.player2_id,
#                 'winner_id': match.winner_id,
#                 'scores': []
#             }
            
#             # Add player names
#             if match.player1_id:
#                 player1 = PlayerProfile.query.get(match.player1_id)
#                 if player1:
#                     match_data['player1_name'] = player1.full_name
            
#             if match.player2_id:
#                 player2 = PlayerProfile.query.get(match.player2_id)
#                 if player2:
#                     match_data['player2_name'] = player2.full_name
            
#             # Add scores
#             scores = MatchScore.query.filter_by(match_id=match.id).order_by(MatchScore.set_number).all()
#             for score in scores:
#                 match_data['scores'].append({
#                     'set': score.set_number,
#                     'player1_score': score.player1_score,
#                     'player2_score': score.player2_score
#                 })
            
#             category_data['matches'].append(match_data)
        
#         result_data['categories'].append(category_data)
    
#     # Return JSON response
#     return jsonify(result_data)

