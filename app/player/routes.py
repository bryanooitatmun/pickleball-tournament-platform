from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
import os
from app import db
from app.player import bp
from app.player.forms import ProfileForm, RegistrationForm
from app.models import PlayerProfile, Tournament, TournamentCategory, Registration, User, TournamentStatus

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
    
    # Get tournaments by status
    upcoming_tournaments = []
    ongoing_tournaments = []
    past_tournaments = []
    
    for registration in registrations:
        tournament = registration.category.tournament
        if tournament.status == TournamentStatus.UPCOMING:
            if tournament not in upcoming_tournaments:
                upcoming_tournaments.append(tournament)
        elif tournament.status == TournamentStatus.ONGOING:
            if tournament not in ongoing_tournaments:
                ongoing_tournaments.append(tournament)
        else:  # COMPLETED
            if tournament not in past_tournaments:
                past_tournaments.append(tournament)
    
    # Sort tournaments by date
    upcoming_tournaments.sort(key=lambda x: x.start_date)
    ongoing_tournaments.sort(key=lambda x: x.start_date)
    past_tournaments.sort(key=lambda x: x.end_date, reverse=True)
    
    return render_template('player/dashboard.html',
                           title='Player Dashboard',
                           profile=profile,
                           upcoming_tournaments=upcoming_tournaments,
                           ongoing_tournaments=ongoing_tournaments,
                           past_tournaments=past_tournaments)

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
@login_required
def register_tournament(tournament_id):
    # Get player profile or redirect to create profile if none exists
    profile = PlayerProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        flash('Please complete your player profile first.', 'warning')
        return redirect(url_for('player.create_profile'))
    
    # Get tournament
    tournament = Tournament.query.get_or_404(tournament_id)
    
    # Check if tournament registration is open
    if not tournament.is_registration_open():
        flash('Registration for this tournament is closed.', 'danger')
        return redirect(url_for('main.tournament_detail', id=tournament_id))
    
    form = RegistrationForm()
    
    # Get categories for this tournament
    categories = tournament.categories.all()
    
    # Populate category choices
    category_choices = [(c.id, c.category_type.value) for c in categories]
    form.category_id.choices = category_choices
    
    # Get potential partners (other players)
    other_players = PlayerProfile.query.filter(PlayerProfile.user_id != current_user.id).all()
    
    # Populate partner choices (for doubles)
    partner_choices = [(0, 'No Partner')] + [(p.id, p.full_name) for p in other_players]
    form.partner_id.choices = partner_choices
    
    if form.validate_on_submit():
        # Check if already registered for this category
        existing_reg = Registration.query.filter_by(
            player_id=profile.id,
            category_id=form.category_id.data
        ).first()
        
        if existing_reg:
            flash('You are already registered for this category.', 'warning')
        else:
            # Create new registration
            registration = Registration(
                player_id=profile.id,
                category_id=form.category_id.data,
                partner_id=form.partner_id.data if form.partner_id.data != 0 else None
            )
            
            db.session.add(registration)
            db.session.commit()
            
            # Redirect to payment page if tournament has a fee
            if tournament.registration_fee > 0:
                return redirect(url_for('player.payment', registration_id=registration.id))
            else:
                flash('You have successfully registered for the tournament!', 'success')
                return redirect(url_for('player.dashboard'))
    
    return render_template('player/register_tournament.html',
                           title='Tournament Registration',
                           tournament=tournament,
                           form=form)

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
    
    # If already paid, redirect to dashboard
    if registration.payment_status == 'paid':
        flash('This registration has already been paid.', 'info')
        return redirect(url_for('player.dashboard'))
    
    if request.method == 'POST':
        # Process payment (in a real app, this would integrate with a payment gateway)
        payment_reference = f"PBT-{int(datetime.utcnow().timestamp())}"
        
        # Update registration with payment info
        registration.payment_status = 'paid'
        registration.payment_date = datetime.utcnow()
        registration.payment_reference = payment_reference
        db.session.commit()
        
        flash('Payment successful! Your tournament registration is confirmed.', 'success')
        return redirect(url_for('player.my_registrations'))
    
    return render_template('player/payment.html',
                          title='Tournament Registration Payment',
                          registration=registration,
                          tournament=tournament)
                          
@bp.route('/my_registrations')
@login_required
def my_registrations():
    # Get player profile
    profile = PlayerProfile.query.filter_by(user_id=current_user.id).first_or_404()
    
    # Get all registrations for this player
    registrations = Registration.query.filter_by(player_id=profile.id).all()
    
    return render_template('player/my_registrations.html',
                           title='My Tournament Registrations',
                           registrations=registrations)

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
