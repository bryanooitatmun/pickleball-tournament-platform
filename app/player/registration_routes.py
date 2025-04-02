from flask import render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import current_user, login_required
from datetime import datetime

from app import db
from app.player import bp # Import the blueprint
# Import necessary models using the new structure
from app.models import (Tournament, TournamentCategory, Registration, PlayerProfile, User,
                       TournamentStatus)
from app.player.forms import PaymentForm, RegistrationForm # Import relevant forms
# Import helpers
from app.helpers.registration import generate_payment_reference, save_payment_proof

# --- Tournament Registration ---

@bp.route('/find_user_by_ic', methods=['POST'])
# No login required? Consider implications if unauthenticated users can query ICs.
# Maybe require login, or add rate limiting/CAPTCHA if kept public.
def find_user_by_ic():
    """Find a user by IC number (AJAX endpoint for partner lookup)"""
    ic_number = request.form.get('ic_number')
    if not ic_number:
        return jsonify({'success': False, 'message': 'No IC number provided'})

    # Find user by IC
    user = User.query.filter_by(ic_number=ic_number).first()

    if not user:
        return jsonify({'success': False, 'message': 'No user found with this IC number'})

    # Check if the found user is the same as the logged-in user (if any)
    if current_user.is_authenticated and user.id == current_user.id:
        return jsonify({
            'success': False,
            'message': 'This is your own IC number. Please enter your partner\'s IC number.'
        })

    # Get profile data to return
    profile = user.player_profile # Assumes relationship is loaded or use query
    if not profile:
         # Handle case where user exists but profile doesn't
         return jsonify({'success': False, 'message': 'User found, but player profile is incomplete.'})

    # Return relevant user/profile data
    return jsonify({
        'success': True,
        'message': 'User found',
        'user': {
            'profile_id': profile.id, # Return profile ID for linking
            'name': profile.full_name or user.full_name,
            'email': user.email,
            'phone': user.phone,
            'nationality': profile.country,
            'date_of_birth': profile.date_of_birth.strftime("%Y-%m-%d") if profile.date_of_birth else None,
            'dupr_id': profile.dupr_id # Assumes dupr_id is on profile
        }
    })

@bp.route('/register_tournament/<int:tournament_id>', methods=['GET', 'POST'])
# Login not strictly required here, but pre-fills form if logged in.
# Handles anonymous registration leading to account creation.
def register_tournament(tournament_id):
    """Register self or a team for a tournament category."""
    tournament = Tournament.query.get_or_404(tournament_id)

    # Check if registration is open
    if not tournament.is_registration_open():
        flash('Registration for this tournament is closed.', 'error')
        return redirect(url_for('main.tournament_detail', id=tournament_id))

    # Sort categories by display_order for the form
    categories = tournament.categories.order_by(TournamentCategory.display_order).all()

    # Get counts of *approved* registrations for capacity checks
    category_counts = {}
    for category in categories:
        approved_regs = Registration.query.filter(
            Registration.category_id == category.id,
            Registration.payment_verified == True # Count only verified/paid
        ).count()

        if category.is_doubles():
            current_participants = approved_regs * 2
        else:
            current_participants = approved_regs

        category_counts[category.id] = {
            'current': current_participants,
            'max': category.max_participants,
            'available': (category.max_participants - current_participants) if category.max_participants is not None else None
        }

    # Create registration form, passing tournament for context if needed by form
    form = RegistrationForm(tournament=tournament)

    # Prefill player1 details if user is logged in and has a profile
    if current_user.is_authenticated and current_user.player_profile:
        profile = current_user.player_profile
        user = current_user # Get user object as well
        form.player1_name.data = profile.full_name or user.full_name
        form.player1_email.data = user.email
        form.player1_email_confirm.data = user.email # Pre-fill confirmation
        form.player1_nationality.data = profile.country
        form.player1_phone.data = user.phone
        form.player1_date_of_birth.data = profile.date_of_birth # Pre-fill DOB
        if user.ic_number:
            form.player1_ic_number.data = user.ic_number
            # Consider making IC read-only if logged in? Depends on workflow.
            # form.player1_ic_number.render_kw = {'readonly': True}
        if profile.dupr_id:
            form.player1_dupr_id.data = profile.dupr_id

    if form.validate_on_submit():
        category = TournamentCategory.query.get(form.category_id.data)
        if not category or category.tournament_id != tournament.id:
             flash('Invalid category selected.', 'danger')
             return redirect(url_for('player.register_tournament', tournament_id=tournament_id))

        # --- Capacity Check ---
        if category.max_participants is not None:
            current_count = category_counts[category.id]['current']
            needed = 2 if category.is_doubles() else 1
            if (current_count + needed) > category.max_participants:
                flash(f'Sorry, the category "{category.name}" is full or does not have enough space.', 'error')
                return redirect(url_for('player.register_tournament', tournament_id=tournament_id))

        is_doubles = category.is_doubles()

        # --- Player 1 Validation ---
        player1_id = None
        user1 = User.query.filter_by(email=form.player1_email.data.lower()).first()

        if current_user.is_authenticated:
            # Ensure logged-in user matches Player 1 email
            if user1 and user1.id != current_user.id:
                 flash('The email provided for Player 1 does not match your logged-in account.', 'error')
                 return redirect(url_for('player.register_tournament', tournament_id=tournament_id))
            if not current_user.player_profile:
                 flash('Please complete your player profile before registering.', 'warning')
                 return redirect(url_for('player.register_tournament', tournament_id=tournament_id)) # Redirect to profile edit
            player1_id = current_user.player_profile.id
        elif user1:
            # Anonymous registration, but email exists - force login
            flash('An account with this email already exists. Please log in before registering.', 'error')
            return redirect(url_for('auth.login', next=request.url))

        # --- Player 2 Validation (Doubles) ---
        player2_id = None
        profile2 = None # To store found partner profile
        if is_doubles:
            # Check if partner was found via IC lookup and ID submitted
            partner_profile_id_str = request.form.get('player2_profile_id')
            if partner_profile_id_str:
                try:
                    partner_profile_id = int(partner_profile_id_str)
                    profile2 = PlayerProfile.query.get(partner_profile_id)
                    if not profile2:
                        flash('Selected partner profile (via IC lookup) not found. Please search again or enter details manually.', 'error')
                        return redirect(url_for('player.register_tournament', tournament_id=tournament_id))
                    player2_id = profile2.id
                    # Ensure partner is not the same as player 1
                    if player1_id and player1_id == player2_id:
                         flash('You cannot register with yourself as a partner.', 'error')
                         return redirect(url_for('player.register_tournament', tournament_id=tournament_id))
                except ValueError:
                     flash('Invalid partner profile ID submitted.', 'error')
                     return redirect(url_for('player.register_tournament', tournament_id=tournament_id))
            else:
                # Partner details entered manually, check if email exists
                user2 = User.query.filter_by(email=form.player2_email.data.lower()).first()
                if user2 and user2.player_profile:
                    player2_id = user2.player_profile.id
                    profile2 = user2.player_profile
                    # Ensure partner is not the same as player 1
                    if player1_id and player1_id == player2_id:
                         flash('You cannot register with yourself as a partner.', 'error')
                         return redirect(url_for('player.register_tournament', tournament_id=tournament_id))


        # --- Check Existing Registrations ---
        # Check if Player 1 is already in this category
        if player1_id and Registration.query.filter(
                (Registration.player_id == player1_id) | (Registration.partner_id == player1_id),
                Registration.category_id == category.id).count() > 0:
            flash('You (Player 1) are already registered for this category.', 'error')
            return redirect(url_for('player.register_tournament', tournament_id=tournament_id))

        # Check if Player 2 is already in this category (if doubles)
        if is_doubles and player2_id and Registration.query.filter(
                (Registration.player_id == player2_id) | (Registration.partner_id == player2_id),
                Registration.category_id == category.id).count() > 0:
            flash('Your selected partner (Player 2) is already registered for this category.', 'error')
            return redirect(url_for('player.register_tournament', tournament_id=tournament_id))

        # Warn about potential conflicts (optional)
        # ... (query other registrations for player1_id and player2_id in the same tournament) ...
        # if conflicts_found: flash(...)

        # --- Create Registration Object ---
        try:
            registration = Registration(
                category_id=category.id,
                registration_fee=category.registration_fee or 0.0,
                is_team_registration=is_doubles,
                player_id=player1_id, # Will be None if anonymous P1
                partner_id=player2_id, # Will be None if singles or anonymous P2

                # Player 1 details (only store if anonymous/not logged in)
                player1_name=form.player1_name.data if not player1_id else None,
                player1_email=form.player1_email.data.lower() if not player1_id else None,
                player1_phone=form.player1_phone.data if not player1_id else None,
                player1_dupr_id=form.player1_dupr_id.data if not player1_id else None,
                player1_date_of_birth=form.player1_date_of_birth.data if not player1_id else None,
                player1_nationality=form.player1_nationality.data if not player1_id else None,
                player1_ic_number=form.player1_ic_number.data if not player1_id else None,

                # Player 2 details (only store if anonymous/not found via IC)
                player2_name=form.player2_name.data if is_doubles and not player2_id else None,
                player2_email=form.player2_email.data.lower() if is_doubles and not player2_id else None,
                player2_phone=form.player2_phone.data if is_doubles and not player2_id else None,
                player2_dupr_id=form.player2_dupr_id.data if is_doubles and not player2_id else None,
                player2_date_of_birth=form.player2_date_of_birth.data if is_doubles and not player2_id else None,
                player2_nationality=form.player2_nationality.data if is_doubles and not player2_id else None,
                player2_ic_number=form.player2_ic_number.data if is_doubles and not player2_id else None,

                # Agreements
                terms_agreement=form.terms_agreement.data,
                liability_waiver=form.liability_waiver.data,
                media_release=form.media_release.data,
                pdpa_consent=form.pdpa_consent.data,

                # Additional information
                special_requests=form.special_requests.data,

                # Generate reference (assuming helper exists)
                payment_reference=generate_payment_reference(tournament)
            )

            # Fetch DUPR ratings (placeholder - needs real implementation)
            # registration.fetch_dupr_ratings()

            db.session.add(registration)
            db.session.commit()

            # If registration fee is zero, approve immediately and create accounts
            if registration.registration_fee <= 0:
                 registration.payment_status = 'free'
                 registration.payment_verified = True
                 registration.is_approved = True
                 registration.payment_verified_at = datetime.utcnow()
                 # Create accounts if needed (will also send emails)
                 registration.create_user_accounts() # Handles commit internally
                 flash('Registration successful! No payment required.', 'success')
                 return redirect(url_for('player.registration_confirmation', registration_id=registration.id))
            else:
                 # Redirect to payment page
                 return redirect(url_for('player.payment', registration_id=registration.id))

        except Exception as e:
             db.session.rollback()
             current_app.logger.error(f"Error creating registration: {e}")
             flash(f"An error occurred during registration: {e}", 'danger')


    # --- Handle GET Request or Validation Failure ---
    elif request.method == 'POST':
        # Form validation failed - flash errors
        for field, errors in form.errors.items():
            for error in errors:
                field_label = getattr(form[field], 'label', None)
                label_text = field_label.text if field_label else field.replace('_', ' ').title()
                flash(f"{label_text}: {error}", 'error')

    return render_template(
        'player/register_tournament.html',
        tournament=tournament,
        form=form,
        categories=categories,
        category_counts=category_counts,
        is_logged_in=current_user.is_authenticated
    )


# --- Payment and Confirmation ---

@bp.route('/payment/<int:registration_id>', methods=['GET', 'POST'])
# No login required here, assumes access via link after registration
def payment(registration_id):
    """Payment page for team registration."""
    registration = Registration.query.get_or_404(registration_id)
    tournament = registration.tournament # Assumes relationship loads tournament

    if not tournament:
         flash('Tournament not found for this registration.', 'error')
         return redirect(url_for('main.index'))

    # If already paid/verified, redirect to confirmation
    if registration.payment_verified:
         flash('This registration has already been paid and verified.', 'info')
         return redirect(url_for('player.registration_confirmation', registration_id=registration.id))
    # If status is free, redirect to confirmation
    if registration.payment_status == 'free':
         return redirect(url_for('player.registration_confirmation', registration_id=registration.id))


    form = PaymentForm() # For CSRF and file upload

    if form.validate_on_submit():
        if not form.payment_proof.data:
             flash('Please select a payment proof file to upload.', 'warning')
        else:
            try:
                # Save payment proof (assuming helper handles validation/saving)
                payment_proof_path = save_payment_proof(form.payment_proof.data, registration.id)

                # Update registration status
                registration.payment_proof = payment_proof_path
                registration.payment_status = 'uploaded' # Pending verification
                registration.payment_proof_uploaded_at = datetime.utcnow()

                # Create user accounts now that payment proof is uploaded
                registration.create_user_accounts() # Handles commit and email sending

                flash('Payment proof uploaded. Registration pending verification. Check email for details.', 'success')
                return redirect(url_for('player.registration_confirmation', registration_id=registration.id))

            except ValueError as e: # Catch specific errors from helper if possible
                flash(f"Error uploading payment proof: {str(e)}", 'danger')
                current_app.logger.error(f"Payment proof upload error for reg {registration_id}: {str(e)}")
            except Exception as e:
                db.session.rollback() # Rollback if account creation or other DB ops fail
                flash("An unexpected error occurred during upload. Please try again.", 'danger')
                current_app.logger.error(f"Unexpected error in payment upload for reg {registration_id}: {str(e)}")

    # Flash form errors if any
    for field, errors in form.errors.items():
        for error in errors:
            flash(f"{getattr(form[field], 'label', field)}: {error}", 'danger')

    return render_template(
        'player/payment.html',
        registration=registration,
        tournament=tournament,
        form=form
    )

@bp.route('/registration_confirmation/<int:registration_id>')
# No login required, confirmation page
def registration_confirmation(registration_id):
    """Registration confirmation page showing status."""
    registration = Registration.query.get_or_404(registration_id)
    tournament = registration.tournament # Assumes relationship loads

    if not tournament:
         # Handle case where tournament might be deleted?
         flash('Associated tournament not found.', 'error')
         return redirect(url_for('main.index'))

    return render_template(
        'player/registration_confirmation.html',
        registration=registration,
        tournament=tournament
    )


# --- Viewing/Managing Own Registrations ---

@bp.route('/my_registrations')
@login_required
def my_registrations():
    # Get player profile - redirect if none exists?
    profile = current_user.player_profile
    if not profile:
         flash("Please create your player profile to view registrations.", "warning")
         return redirect(url_for('player.create_profile'))

    # Get all registrations where user is player1 or player2 (partner)
    registrations = Registration.query.filter(
        (Registration.player_id == profile.id) | (Registration.partner_id == profile.id)
    ).join(Registration.category).join(Tournament).order_by(
        Tournament.start_date.desc(), # Show newest tournaments first
        TournamentCategory.display_order # Order by category within tournament
    ).all()
    
    # Group by tournament for display (optional, could display linearly)
    tournaments_data = {}
    for reg in registrations:
        tournament = reg.tournament # Assumes relationship loaded
        if tournament.id not in tournaments_data:
            tournaments_data[tournament.id] = {
                'tournament': tournament,
                'registrations': []
            }
        tournaments_data[tournament.id]['registrations'].append(reg)
    
    # Sort tournaments by date if grouping (newest first)
    sorted_tournaments = sorted(tournaments_data.values(), key=lambda t: t['tournament'].start_date or datetime.min, reverse=True)

    return render_template('player/my_registrations.html',
                           title='My Tournament Registrations',
                           # Pass either grouped or flat list
                           tournaments=sorted_tournaments
                           # registrations=registrations # Alternative: pass flat list
                           )


@bp.route('/cancel_registration/<int:registration_id>', methods=['POST'])
@login_required
def cancel_registration(registration_id):
    registration = Registration.query.get_or_404(registration_id)
    profile = current_user.player_profile

    # Verify this registration belongs to the current user (as player 1 or 2)
    if not profile or (registration.player_id != profile.id and registration.partner_id != profile.id):
        flash('You do not have permission to cancel this registration.', 'danger')
        return redirect(url_for('player.my_registrations'))

    # Check if cancellation is allowed (e.g., before deadline or tournament start)
    tournament = registration.tournament
    if not tournament or tournament.status != TournamentStatus.UPCOMING:
        flash('Cannot cancel registration for tournaments that are ongoing or completed.', 'danger')
        return redirect(url_for('player.my_registrations'))
    # Optional: Check against registration_deadline
    # if tournament.registration_deadline and datetime.utcnow() > tournament.registration_deadline:
    #     flash('The registration deadline has passed. Cannot cancel registration.', 'danger')
    #     return redirect(url_for('player.my_registrations'))

    # Check if payment was made (policy for refunds?)
    if registration.payment_status == 'paid' or registration.payment_verified:
         flash('Registration has been paid. Please contact the organizer regarding cancellations and refunds.', 'warning')
         return redirect(url_for('player.my_registrations'))

    try:
        # Delete the registration record
        db.session.delete(registration)
        db.session.commit()
        flash('Your tournament registration has been cancelled.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error cancelling registration: {e}', 'danger')

    return redirect(url_for('player.my_registrations'))