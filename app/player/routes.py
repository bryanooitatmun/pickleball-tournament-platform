from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
import os
import requests
from app import db
from app.player import bp
from app.models import Tournament, TournamentCategory, Registration, PlayerProfile, User, UserRole, TournamentStatus
from app.player.forms import TournamentRegistrationForm, PaymentForm, RegistrationForm, ProfileForm
from app.helpers.registration import generate_payment_reference, generate_temp_password, save_picture
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


@bp.route('/register_tournament/<int:tournament_id>', methods=['GET', 'POST'])
def register_tournament(tournament_id):
    """Register a team for a tournament without requiring login"""
    tournament = Tournament.query.get_or_404(tournament_id)
    
    # Check if registration is open
    if not tournament.is_registration_open():
        flash('Registration for this tournament is closed.', 'error')
        return redirect(url_for('main.tournament_detail', id=tournament_id))
    
    # Sort categories by display_order
    categories = tournament.categories.order_by(TournamentCategory.display_order).all()
    
    # Create registration form
    form = RegistrationForm(tournament=tournament)
    
    if form.validate_on_submit():
        category = TournamentCategory.query.get(form.category_id.data)
        is_doubles = category.is_doubles()

        # Create registration
        registration = Registration(
            category_id=form.category_id.data,
            registration_fee=category.registration_fee,
            is_team_registration=is_doubles,
            
            # Player 1 details
            player1_name=form.player1_name.data,
            player1_email=form.player1_email.data,
            player1_phone=form.player1_phone.data,
            player1_dupr_id=form.player1_dupr_id.data,
            player1_date_of_birth=form.player1_date_of_birth.data,
            player1_nationality=form.player1_nationality.data,
            
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
        if is_doubles:
            registration.player2_name = form.player2_name.data
            registration.player2_email = form.player2_email.data
            registration.player2_phone = form.player2_phone.data
            registration.player2_dupr_id = form.player2_dupr_id.data
            registration.player2_date_of_birth = form.player2_date_of_birth.data
            registration.player2_nationality = form.player2_nationality.data
        
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
    
    return render_template(
        'player/register_tournament.html',
        tournament=tournament,
        form=form,
        categories=categories
    )

@bp.route('/payment/<int:registration_id>', methods=['GET', 'POST'])
def payment(registration_id):
    """Payment page for team registration"""
    registration = Registration.query.get_or_404(registration_id)
    tournament = registration.tournament
    
    # Create form for CSRF protection and file validation
    form = PaymentForm()
    
    # Handle payment form submission
    if form.validate_on_submit():
        # Process payment proof upload
        if form.payment_proof.data:
            payment_proof = form.payment_proof.data
            # Save payment proof
            filename = secure_filename(f"payment_{registration.id}_{payment_proof.filename}")
            payment_proof.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            
            # Update registration
            registration.payment_proof = filename
            registration.payment_status = 'uploaded'  # Pending verification
            registration.payment_proof_uploaded_at = datetime.utcnow()
            
            # Create user accounts for both players
            try:
                registration.create_user_accounts()
            except Exception as e:
                current_app.logger.error(f"Error creating user accounts: {e}")
                flash("Could not create user accounts. Please contact support.", "warning")
            
            # Send confirmation emails
            try:
                registration.send_confirmation_emails()
            except Exception as e:
                current_app.logger.error(f"Error sending confirmation emails: {e}")
                flash("Could not send confirmation emails. Please contact support.", "warning")
            
            db.session.commit()
            
            flash('Your payment proof has been uploaded. Registration is pending verification. Check your email for confirmation and account details.', 'success')
            return redirect(url_for('player.registration_confirmation', registration_id=registration.id))
    
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

def save_payment_proof(proof_file, registration_id):
    """Save uploaded payment proof and return file path"""
    if not proof_file:
        return None
        
    # Generate a secure filename
    filename = secure_filename(proof_file.filename)
    
    # Generate a unique filename
    unique_filename = f"payment_proof_{registration_id}_{int(datetime.utcnow().timestamp())}_{filename}"
    
    # Create full path
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'payment_proofs', unique_filename)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Save the file
    proof_file.save(file_path)
    
    # Return the relative path for the database
    return os.path.join('uploads', 'payment_proofs', unique_filename)
    