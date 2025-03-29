from flask import render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
import os
import requests
from app import db
from app.player import bp
from app.models import Tournament, TournamentCategory, Registration, PlayerProfile, User, UserRole, TournamentStatus
from app.player.forms import PaymentForm, RegistrationForm, ProfileForm, ChangePasswordForm
from app.helpers.registration import generate_payment_reference, generate_temp_password, save_picture, save_payment_proof
from datetime import datetime


@bp.route('/dashboard')
@login_required
def dashboard():
    # Get player profile or redirect to create profile if none exists
    profile = PlayerProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        flash('Please complete your player profile first.', 'warning')
        return redirect(url_for('player.create_profile'))
    
    # Get registrations for this player
    registrations = []
    registrations_player = Registration.query.filter_by(player_id=profile.id).all()
    registrations_partner = Registration.query.filter_by(partner_id=profile.id).all()

    registrations.extend(registrations_player)
    registrations.extend(registrations_partner)

    # Prepare data structures for the dashboard
    upcoming_tournaments = []
    ongoing_tournaments = []
    past_tournaments = []
    
    # Stats to display
    stats = {
        'total_tournaments': 0,
        'completed_tournaments': 0,
        'upcoming_tournaments': 0,
        'pending_payments': 0,
        'rejected_payments': 0
    }
    
    # Group registrations by tournament
    tournament_data = {}
    for registration in registrations:
        tournament = registration.category.tournament
        tournament_id = tournament.id
        
        if tournament_id not in tournament_data:
            tournament_data[tournament_id] = {
                'tournament': tournament,
                'registrations': []
            }
        
        tournament_data[tournament_id]['registrations'].append(registration)
        
        # Count payment statuses
        if registration.payment_status == 'pending':
            stats['pending_payments'] += 1
        elif registration.payment_status == 'rejected':
            stats['rejected_payments'] += 1
    
    # Sort tournaments by date and status
    for tournament_id, data in tournament_data.items():
        tournament = data['tournament']
        if tournament.status == TournamentStatus.UPCOMING:
            upcoming_tournaments.append(data)
            stats['upcoming_tournaments'] += 1
        elif tournament.status == TournamentStatus.ONGOING:
            ongoing_tournaments.append(data)
        else:  # COMPLETED
            # Add tournament results for past tournaments
            tournament_results = []
            for registration in data['registrations']:
                category = registration.category
                result = {
                    'category': category.category_type.value,
                    'place': None,
                    'points': 0
                }
                
                # In a real app, you'd query the actual results
                # This is a placeholder for demonstration
                if tournament.winners_by_category and category.category_type.value in tournament.winners_by_category:
                    winners = tournament.winners_by_category[category.category_type.value]
                    
                    # Check if this player is the winner
                    if 1 in winners:
                        if winners[1] == profile or (isinstance(winners[1], list) and profile in winners[1]):
                            result['place'] = 1
                            result['points'] = category.points_awarded
                    
                    # Check if this player is the runner-up
                    if 2 in winners:
                        if winners[2] == profile or (isinstance(winners[2], list) and profile in winners[2]):
                            result['place'] = 2
                            result['points'] = int(category.points_awarded * 0.7)  # Example calculation
                
                tournament_results.append(result)
            
            # Add results to the tournament data
            data['results'] = tournament_results
            past_tournaments.append(data)
            stats['completed_tournaments'] += 1
    
    # Sort upcoming tournaments by start date
    upcoming_tournaments.sort(key=lambda x: x['tournament'].start_date)
    
    # Sort past tournaments by end date (most recent first)
    past_tournaments.sort(key=lambda x: x['tournament'].end_date, reverse=True)
    
    # Set total tournaments count
    stats['total_tournaments'] = len(upcoming_tournaments) + len(ongoing_tournaments) + len(past_tournaments)
    
    return render_template('player/dashboard.html',
                           title='Player Dashboard',
                           profile=profile,
                           upcoming_tournaments=upcoming_tournaments,
                           ongoing_tournaments=ongoing_tournaments,
                           past_tournaments=past_tournaments,
                           stats=stats)

@bp.route('/create_profile', methods=['GET', 'POST'])
@login_required
def create_profile():
    # Check if user already has a profile
    existing_profile = PlayerProfile.query.filter_by(user_id=current_user.id).first()
    if existing_profile:
        return redirect(url_for('player.edit_profile'))
    
    form = ProfileForm()
    if form.validate_on_submit():
        profile = PlayerProfile(
            user_id=current_user.id,
            full_name=form.full_name.data,
            country=form.country.data,
            city=form.city.data,
            age=form.age.data,
            bio=form.bio.data,
            plays=form.plays.data,
            height=form.height.data,
            paddle=form.paddle.data,
            instagram=form.instagram.data,
            facebook=form.facebook.data,
            twitter=form.twitter.data,
            turned_pro=form.turned_pro.data
        )
        
        # Handle profile image
        if form.profile_image.data:
            profile.profile_image = save_picture(form.profile_image.data, 'profile_pics')
        
        # Handle action image
        if form.action_image.data:
            profile.action_image = save_picture(form.action_image.data, 'action_pics')
        
        # Handle banner image
        if form.banner_image.data:
            profile.banner_image = save_picture(form.banner_image.data, 'banner_pics')
        
        db.session.add(profile)
        db.session.commit()
        
        flash('Your player profile has been created!', 'success')
        return redirect(url_for('player.dashboard'))
    
    return render_template('player/create_profile.html',
                           title='Create Player Profile',
                           form=form)

@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    profile = PlayerProfile.query.filter_by(user_id=current_user.id).first_or_404()
    form = ProfileForm(obj=profile)
    
    if form.validate_on_submit():
        profile.full_name = form.full_name.data
        profile.country = form.country.data
        profile.city = form.city.data
        profile.age = form.age.data
        profile.bio = form.bio.data
        profile.plays = form.plays.data
        profile.height = form.height.data
        profile.paddle = form.paddle.data
        profile.instagram = form.instagram.data
        profile.facebook = form.facebook.data
        profile.twitter = form.twitter.data
        profile.turned_pro = form.turned_pro.data
        
        # Handle profile image
        if form.profile_image.data:
            profile.profile_image = save_picture(form.profile_image.data, 'profile_pics')
        
        # Handle action image
        if form.action_image.data:
            profile.action_image = save_picture(form.action_image.data, 'action_pics')
        
        # Handle banner image
        if form.banner_image.data:
            profile.banner_image = save_picture(form.banner_image.data, 'banner_pics')
        
        db.session.commit()
        
        flash('Your player profile has been updated!', 'success')
        return redirect(url_for('player.dashboard'))
    
    return render_template('player/edit_profile.html',
                           title='Edit Player Profile',
                           form=form,
                           profile=profile)


# @bp.route('/register_tournament/<int:tournament_id>', methods=['GET', 'POST'])
# def register_tournament(tournament_id):
#     # Get tournament
#     tournament = Tournament.query.get_or_404(tournament_id)
    
#     # Check if tournament registration is open
#     if not tournament.is_registration_open():
#         flash('Registration for this tournament is closed.', 'danger')
#         return redirect(url_for('main.tournament_detail', id=tournament_id))
    
#     form = TournamentRegistrationForm()
#     form.tournament_id.data = tournament_id
    
#     # Get categories for this tournament
#     categories = tournament.categories.all()
    
#     # Populate category choices
#     category_choices = [(c.id, c.category_type.value) for c in categories]
#     form.category_id.choices = category_choices
    
#     # Get potential partners (other players)
#     other_players = PlayerProfile.query.filter(PlayerProfile.id != 0).all()
    
#     # Populate partner choices (for doubles)
#     partner_choices = [(0, 'No Partner')] + [(p.id, p.full_name) for p in other_players]
#     form.partner_id.choices = partner_choices
    
#     # Check if user is authenticated
#     is_authenticated = current_user.is_authenticated
    
#     # If GET request or form validation fails
#     selected_category = None
#     if request.args.get('category'):
#         category_id = int(request.args.get('category'))
#         selected_category = TournamentCategory.query.get(category_id)
#         form.category_id.data = category_id
    
#     return render_template('player/register_tournament.html',
#                            title='Tournament Registration',
#                            tournament=tournament,
#                            form=form,
#                            is_authenticated=is_authenticated,
#                            selected_category=selected_category)

#TODO: Is this a security concern?
@bp.route('/find_user_by_ic', methods=['POST'])
def find_user_by_ic():
    """Find a user by IC number (AJAX endpoint)"""
    ic_number = request.form.get('ic_number')
    if not ic_number:
        return jsonify({'success': False, 'message': 'No IC number provided'})
    
    # Find player profile with this IC number
    user = User.query.filter_by(ic_number=ic_number).first()
    
    if not user:
        return jsonify({'success': False, 'message': 'No user found with this IC number'})
        
    profile = PlayerProfile.query.filter_by(user_id=user.id).first()
    # If current user is authenticated, check if this is their own profile
    if current_user.is_authenticated and current_user.ic_number == ic_number:
        return jsonify({
            'success': False,
            'message': 'This is your own IC number. Please enter your partner\'s IC number.'
        })
    
    # Return user data
    return jsonify({
        'success': True,
        'message': 'User found',
        'user': {
            'id': user.id,
            'name': user.full_name,
            'email': user.email,
            'phone': user.phone,
            'nationality': profile.country,
            'date_of_birth': profile.date_of_birth.strftime("%Y-%m-%d"),
            'dupr_id': profile.dupr_id if hasattr(profile, 'dupr_id') else None
        }
    })

@bp.route('/register_tournament/<int:tournament_id>', methods=['GET', 'POST'])
def register_tournament(tournament_id):
    """Register a team for a tournament"""
    tournament = Tournament.query.get_or_404(tournament_id)
    
    # Check if registration is open
    if not tournament.is_registration_open():
        flash('Registration for this tournament is closed.', 'error')
        return redirect(url_for('main.tournament_detail', id=tournament_id))
    
    # Sort categories by display_order
    categories = tournament.categories.order_by(TournamentCategory.display_order).all()
    
    # Get counts of approved registrations for each category
    category_counts = {}
    for category in categories:
        if category.is_doubles():
            count = Registration.query.filter_by(
                category_id=category.id, 
                payment_status='paid'
            ).count()
            
            category_counts[category.id] = {
                'current': count * 2,
                'max': category.max_participants,
                'available': category.max_participants - count * 2 if category.max_participants else None
            }
        else:
            count = Registration.query.filter_by(
                category_id=category.id, 
                payment_status='paid'
            ).count()
            
            category_counts[category.id] = {
                'current': count * 2,
                'max': category.max_participants,
                'available': category.max_participants - count if category.max_participants else None
            }
    
    # Create registration form
    form = RegistrationForm(tournament=tournament)
    
    # Prefill player1 details if user is logged in
    if current_user.is_authenticated and current_user.player_profile:
        profile = current_user.player_profile
        form.player1_name.data = profile.full_name
        form.player1_email.data = current_user.email
        form.player1_email_confirm.data = current_user.email
        form.player1_nationality.data = profile.country
        form.player1_phone.data = user.phone
        if hasattr(profile, 'ic_number') and current_user.ic_number:
            form.player1_ic_number.data = current_user.ic_number
            form.player1_ic_number.render_kw = {'readonly': True}
        
        # Set other fields if they exist
        if hasattr(profile, 'dupr_id') and profile.dupr_id:
            form.player1_dupr_id.data = profile.dupr_id
    
    if form.validate_on_submit():
        category = TournamentCategory.query.get(form.category_id.data)
        
        # Check if category is full
        if category.max_participants:
            current_count = category_counts[category.id]['current']
            if current_count >= category.max_participants:
                flash(f'Sorry, this category is already full.', 'error')
                return redirect(url_for('player.register_tournament', tournament_id=tournament_id))
        
        is_doubles = category.is_doubles()
        
        # Check if player1 email already exists
        user1 = User.query.filter_by(email=form.player1_email.data).first()
        if user1 and not current_user.is_authenticated:
            flash('An account with this email already exists. Please log in before registering.', 'error')
            # Redirect to login page with next parameter to return to registration
            return redirect(url_for('auth.login', next=url_for('player.register_tournament', tournament_id=tournament_id)))

        # If user is logged in, use their player profile
        if current_user.is_authenticated and current_user.player_profile:
            player1_id = current_user.player_profile.id
        else:
            player1_id = None
        
        # Check if player2 email already exists if this is a doubles category
        player2_id = None
        if is_doubles:
            # Check if player2_profile_id was provided (from the find user functionality)
            player2_profile_id = request.form.get('player2_profile_id')
            if player2_profile_id:
                player2_id = int(player2_profile_id)
                # Verify that the profile exists
                profile2 = PlayerProfile.query.get(player2_id)
                if not profile2:
                    flash('Selected partner profile not found. Please try again.', 'error')
                    return redirect(url_for('player.register_tournament', tournament_id=tournament_id))
            else:
                user2 = User.query.filter_by(email=form.player2_email.data).first()
                if user2 and user2.player_profile:
                    player2_id = user2.player_profile.id
        
        # Check if players are already registered for this category
        existing_registration1 = Registration.query.filter_by(
            category_id=category.id,
            player_id=player1_id
        ).first() if player1_id else None
        
        existing_registration2 = Registration.query.filter_by(
            category_id=category.id,
            partner_id=player2_id
        ).first() if player2_id else None
        
        if existing_registration1:
            flash('You are already registered for this category.', 'error')
            return redirect(url_for('player.register_tournament', tournament_id=tournament_id))
        
        if existing_registration2:
            flash('Your selected partner is already registered for this category.', 'error')
            return redirect(url_for('player.register_tournament', tournament_id=tournament_id))
        
        player_registrations = Registration.query.filter(
            Registration.category.has(tournament_id=tournament.id),
            (Registration.player_id == player1_id) | (Registration.partner_id == player1_id)
        ).all() if player1_id else []

        partner_registrations = Registration.query.filter(
            Registration.category.has(tournament_id=tournament.id),
            (Registration.player_id == player2_id) | (Registration.partner_id == player2_id)
        ).all() if player2_id else []

        if player_registrations:
            flash('You are already registered for other categories in this tournament. Please check the schedule for potential conflicts.', 'warning')

        if partner_registrations:
            flash('Your partner is already registered for other categories in this tournament. Please check the schedule for potential conflicts.', 'warning')

        # Create registration
        registration = Registration(
            category_id=form.category_id.data,
            registration_fee=category.registration_fee,
            is_team_registration=is_doubles,
            player_id=player1_id,
            partner_id=player2_id,
            
            # Player 1 details (only set if not using existing profile)
            player1_name=form.player1_name.data if not player1_id else None,
            player1_email=form.player1_email.data if not player1_id else None,
            player1_phone=form.player1_phone.data if not player1_id else None,
            player1_dupr_id=form.player1_dupr_id.data if not player1_id else None,
            player1_date_of_birth=form.player1_date_of_birth.data if not player1_id else None,
            player1_nationality=form.player1_nationality.data if not player1_id else None,
            player1_ic_number=form.player1_ic_number.data if not player1_id else None,
            
            # Agreements
            terms_agreement=form.terms_agreement.data,
            liability_waiver=form.liability_waiver.data,
            media_release=form.media_release.data,
            pdpa_consent=form.pdpa_consent.data,
            
            # Additional information
            special_requests=form.special_requests.data,
            
            # Generate reference
            payment_reference=generate_payment_reference(tournament)
        )
        
        # Add player 2 details for doubles
        if is_doubles and not player2_id:
            registration.player2_name = form.player2_name.data
            registration.player2_email = form.player2_email.data
            registration.player2_phone = form.player2_phone.data
            registration.player2_dupr_id = form.player2_dupr_id.data
            registration.player2_date_of_birth = form.player2_date_of_birth.data
            registration.player2_nationality = form.player2_nationality.data
            registration.player2_ic_number = form.player2_ic_number.data
        
        # Fetch DUPR ratings from API
        try:
            registration.fetch_dupr_ratings()
        except Exception as e:
            current_app.logger.error(f"Error fetching DUPR ratings: {e}")
            flash("Could not fetch DUPR ratings. Registration will proceed, but please contact support.", "warning")
        
        # Add to database
        db.session.add(registration)
        db.session.commit()
        
        # Redirect to payment page
        return redirect(url_for('player.payment', registration_id=registration.id))
    
    elif request.method == 'POST':
        # Form validation failed - convert validation errors to flash messages
        for field, errors in form.errors.items():
            for error in errors:
                field_label = form[field].label.text if hasattr(form[field], 'label') and form[field].label else field
                flash(f"{field_label}: {error}", 'error')

    return render_template(
        'player/register_tournament.html',
        tournament=tournament,
        form=form,
        categories=categories,
        category_counts=category_counts,
        is_logged_in=current_user.is_authenticated
    )

@bp.route('/payment/<int:registration_id>', methods=['GET', 'POST'])
def payment(registration_id):
    """Payment page for team registration"""
    registration = Registration.query.get_or_404(registration_id)
    tournament = registration.tournament
    
    # Create form for CSRF protection and file validation
    form = PaymentForm()
    
    # # Check for upload error from session (set by the error handler)
    # if 'upload_error' in session:
    #     flash(session.pop('upload_error'), 'danger')
    
    # Handle payment form submission
    if form.validate_on_submit():
        try:
            # Process payment proof upload
            if form.payment_proof.data:
                # Save payment proof with resize
                payment_proof_path = save_payment_proof(form.payment_proof.data, registration.id)
                
                # Update registration
                registration.payment_proof = payment_proof_path
                registration.payment_status = 'uploaded'  # Pending verification
                registration.payment_proof_uploaded_at = datetime.utcnow()
                
                # Create user accounts for both players if they don't exist already
                try:
                    registration.create_user_accounts()
                except Exception as e:
                    current_app.logger.error(f"Error creating user accounts: {e}")
                    flash(f"Could not create user accounts. Error: {e}. Please contact support.", "warning")
                
                db.session.commit()
                
                flash('Your payment proof has been uploaded. Registration is pending verification. Check your email for confirmation and account details.', 'success')
                return redirect(url_for('player.registration_confirmation', registration_id=registration.id))
        except ValueError as e:
            flash(f"Error uploading payment proof: {str(e)}", 'danger')
            current_app.logger.error(f"Payment proof upload error: {str(e)}")
        except Exception as e:
            flash("An unexpected error occurred. Please try again with a smaller image file.", 'danger')
            current_app.logger.error(f"Unexpected error in payment upload: {str(e)}")
    
    # If there are form errors, flash them
    for field, errors in form.errors.items():
        for error in errors:
            flash(f"{form[field].label.text}: {error}", 'danger')
    
    return render_template(
        'player/payment.html',
        registration=registration,
        tournament=tournament,
        form=form
    )

@bp.route('/registration_confirmation/<int:registration_id>')
def registration_confirmation(registration_id):
    """Registration confirmation page"""
    registration = Registration.query.get_or_404(registration_id)
    tournament = registration.tournament
    
    return render_template(
        'player/registration_confirmation.html',
        registration=registration,
        tournament=tournament
    )

@bp.route('/my_registrations')
@login_required
def my_registrations():
    # Get player profile
    profile = PlayerProfile.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Get all registrations for this player
    registrations = Registration.query.filter_by(player_id=profile.id).all()
    
    # Group by tournament
    tournaments = {}
    for reg in registrations:
        tournament = reg.category.tournament
        if tournament.id not in tournaments:
            tournaments[tournament.id] = {
                'tournament': tournament,
                'registrations': []
            }
        tournaments[tournament.id]['registrations'].append(reg)
    
    return render_template('player/my_registrations.html',
                           title='My Tournament Registrations',
                           tournaments=tournaments.values())


@bp.route('/cancel_registration/<int:registration_id>', methods=['POST'])
@login_required
def cancel_registration(registration_id):
    # Get registration
    registration = Registration.query.get_or_404(registration_id)
    
    # Verify this belongs to the current user
    profile = PlayerProfile.query.filter_by(user_id=current_user.id).first_or_404()
    if registration.player_id != profile.id:
        flash('You do not have permission to cancel this registration.', 'danger')
        return redirect(url_for('player.my_registrations'))
    
    # Check if tournament is still upcoming (can't cancel if already started)
    tournament = registration.category.tournament
    if tournament.status != TournamentStatus.UPCOMING:
        flash('Cannot cancel registration for tournaments that have already started.', 'danger')
        return redirect(url_for('player.my_registrations'))
    
    # Delete registration
    db.session.delete(registration)
    db.session.commit()
    
    flash('Your tournament registration has been cancelled.', 'success')
    return redirect(url_for('player.my_registrations'))

@bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash('Your password has been updated!', 'success')
            return redirect(url_for('player.dashboard'))
        else:
            flash('Current password is incorrect.', 'danger')
    
    return render_template('player/change_password.html', title='Change Password', form=form)
    