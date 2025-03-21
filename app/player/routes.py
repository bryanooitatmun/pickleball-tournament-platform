from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
import os
from app import db
from app.player import bp
from app.models import Tournament, TournamentCategory, Registration, PlayerProfile, User, UserRole
from app.player.forms import TournamentRegistrationForm, PaymentProofForm

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def save_picture(picture, subfolder='profile_pics'):
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
def dashboard():
    # Get player profile or redirect to create profile if none exists
    profile = PlayerProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        flash('Please complete your player profile first.', 'warning')
        return redirect(url_for('player.create_profile'))
    
    # Get registrations for this player
    registrations = Registration.query.filter_by(player_id=profile.id).all()
    
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


@bp.route('/register_tournament/<int:tournament_id>', methods=['GET', 'POST'])
def register_tournament(tournament_id):
    # Get tournament
    tournament = Tournament.query.get_or_404(tournament_id)
    
    # Check if tournament registration is open
    if not tournament.is_registration_open():
        flash('Registration for this tournament is closed.', 'danger')
        return redirect(url_for('main.tournament_detail', id=tournament_id))
    
    form = TournamentRegistrationForm()
    form.tournament_id.data = tournament_id
    
    # Get categories for this tournament
    categories = tournament.categories.all()
    
    # Populate category choices
    category_choices = [(c.id, c.category_type.value) for c in categories]
    form.category_id.choices = category_choices
    
    # Get potential partners (other players)
    other_players = PlayerProfile.query.filter(PlayerProfile.id != 0).all()
    
    # Populate partner choices (for doubles)
    partner_choices = [(0, 'No Partner')] + [(p.id, p.full_name) for p in other_players]
    form.partner_id.choices = partner_choices
    
    # Check if user is authenticated
    is_authenticated = current_user.is_authenticated
    
    if form.validate_on_submit():
        # Additional validation for non-authenticated users
        if not form.validate_registration(is_authenticated):
            return render_template('player/register_tournament.html',
                                  title='Tournament Registration',
                                  tournament=tournament,
                                  form=form,
                                  is_authenticated=is_authenticated)
        
        # Handle user creation if not logged in
        if not is_authenticated:
            # Create new user
            user = User(
                username=form.email.data.split('@')[0],  # Generate username from email
                email=form.email.data.lower(),
                role=UserRole.PLAYER
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            
            # Create player profile
            profile = PlayerProfile(
                user_id=user.id,
                full_name=form.full_name.data,
                email=form.email.data.lower(),
                phone=form.phone.data,
                country=form.country.data,
                city=form.city.data,
                gender=form.gender.data,
                date_of_birth=form.date_of_birth.data
            )
            db.session.add(profile)
            db.session.commit()
            
            # Log in the new user
            login_user(user)
            
            flash('Your account has been created and you are now logged in.', 'success')
        else:
            # Get existing player profile
            profile = PlayerProfile.query.filter_by(user_id=current_user.id).first()
            
            # Create profile if it doesn't exist
            if not profile:
                profile = PlayerProfile(
                    user_id=current_user.id,
                    full_name=current_user.username,  # Use username as fallback
                    email=current_user.email
                )
                db.session.add(profile)
                db.session.commit()
        
        # Get the selected category
        selected_category = TournamentCategory.query.get(form.category_id.data)
        
        # Check if already registered for this category
        existing_reg = Registration.query.filter_by(
            player_id=profile.id,
            category_id=form.category_id.data
        ).first()
        
        if existing_reg:
            flash('You are already registered for this category.', 'warning')
            return redirect(url_for('player.dashboard'))
        else:
            # Generate a reference number
            reference = f"{tournament.payment_reference_prefix or 'PBT'}-{int(datetime.utcnow().timestamp())}"
            
            # Create new registration
            registration = Registration(
                player_id=profile.id,
                category_id=form.category_id.data,
                partner_id=form.partner_id.data if form.partner_id.data != 0 else None,
                dupr_rating=form.dupr_rating.data,
                emergency_contact=form.emergency_contact.data,
                emergency_phone=form.emergency_phone.data,
                shirt_size=form.shirt_size.data,
                special_requests=form.special_requests.data,
                payment_reference=reference,
                payment_status='pending'
            )
            
            db.session.add(registration)
            db.session.commit()
            
            # Redirect to payment page if category has a fee
            if selected_category.registration_fee > 0:
                return redirect(url_for('player.payment', registration_id=registration.id))
            else:
                # Free registration
                registration.payment_status = 'free'
                registration.is_approved = True
                db.session.commit()
                
                flash('You have successfully registered for the tournament!', 'success')
                return redirect(url_for('player.dashboard'))
    
    # If GET request or form validation fails
    selected_category = None
    if request.args.get('category'):
        category_id = int(request.args.get('category'))
        selected_category = TournamentCategory.query.get(category_id)
        form.category_id.data = category_id
    
    return render_template('player/register_tournament.html',
                           title='Tournament Registration',
                           tournament=tournament,
                           form=form,
                           is_authenticated=is_authenticated,
                           selected_category=selected_category)

@bp.route('/payment/<int:registration_id>', methods=['GET', 'POST'])
@login_required
def payment(registration_id):
    registration = Registration.query.get_or_404(registration_id)
    
    # Ensure this registration belongs to the current user
    profile = PlayerProfile.query.filter_by(user_id=current_user.id).first_or_404()
    if registration.player_id != profile.id:
        flash('You do not have permission to access this payment.', 'danger')
        return redirect(url_for('player.dashboard'))
    
    tournament = registration.category.tournament
    category = registration.category
    
    # If already paid, redirect to dashboard
    if registration.payment_status in ['paid', 'free']:
        flash('This registration has already been paid.', 'info')
        return redirect(url_for('player.dashboard'))
    
    form = PaymentProofForm()
    form.registration_id.data = registration_id
    
    if form.validate_on_submit():
        # Save payment proof
        proof_path = save_payment_proof(form.payment_proof.data, registration_id)
        
        # Update registration with payment info
        registration.payment_proof = proof_path
        registration.payment_proof_uploaded_at = datetime.utcnow()
        registration.payment_notes = form.payment_notes.data
        registration.payment_status = 'uploaded'  # Pending verification by organizer
        db.session.commit()
        
        flash('Payment proof uploaded successfully! Your registration will be confirmed once the organizer verifies your payment.', 'success')
        return redirect(url_for('player.my_registrations'))
    
    return render_template('player/payment.html',
                          title='Tournament Registration Payment',
                          registration=registration,
                          tournament=tournament,
                          category=category,
                          form=form)

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
    