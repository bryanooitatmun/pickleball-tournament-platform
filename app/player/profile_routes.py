from flask import render_template, redirect, url_for, flash, request
from flask_login import current_user, login_required

from app import db
from app.player import bp # Import the blueprint
from app.models import PlayerProfile # Use new import path
from app.player.forms import ProfileForm, ChangePasswordForm # Import relevant forms
from app.helpers.registration import save_picture # Assuming this helper handles image saving

@bp.route('/create_profile', methods=['GET', 'POST'])
@login_required
def create_profile():
    # Check if user already has a profile
    existing_profile = PlayerProfile.query.filter_by(user_id=current_user.id).first()
    if existing_profile:
        flash('You already have a player profile. Redirecting to edit page.', 'info')
        return redirect(url_for('player.edit_profile'))

    form = ProfileForm()
    # Pre-fill name and email from user account if possible
    if request.method == 'GET':
         form.full_name.data = current_user.full_name or ''
         # Email is usually not on profile form, but handled via User model

    if form.validate_on_submit():
        profile = PlayerProfile(user_id=current_user.id)
        form.populate_obj(profile) # Populate basic fields

        # Handle image uploads
        try:
            if form.profile_image.data:
                profile.profile_image = save_picture(form.profile_image.data, 'profile_pics')
            if form.action_image.data:
                profile.action_image = save_picture(form.action_image.data, 'action_pics')
            if form.banner_image.data:
                profile.banner_image = save_picture(form.banner_image.data, 'banner_pics')

            db.session.add(profile)
            db.session.commit()
            flash('Your player profile has been created!', 'success')
            return redirect(url_for('player.dashboard'))
        except Exception as e:
             db.session.rollback()
             flash(f'Error creating profile: {e}', 'danger')

    return render_template('player/create_profile.html',
                           title='Create Player Profile',
                           form=form)

@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    profile = PlayerProfile.query.filter_by(user_id=current_user.id).first_or_404()
    form = ProfileForm(obj=profile)

    if form.validate_on_submit():
        form.populate_obj(profile) # Update basic fields

        # Handle image uploads only if new files are provided
        try:
            if form.profile_image.data:
                profile.profile_image = save_picture(form.profile_image.data, 'profile_pics')
            if form.action_image.data:
                profile.action_image = save_picture(form.action_image.data, 'action_pics')
            if form.banner_image.data:
                profile.banner_image = save_picture(form.banner_image.data, 'banner_pics')

            db.session.commit()
            flash('Your player profile has been updated!', 'success')
            return redirect(url_for('player.dashboard'))
        except Exception as e:
             db.session.rollback()
             flash(f'Error updating profile: {e}', 'danger')

    return render_template('player/edit_profile.html',
                           title='Edit Player Profile',
                           form=form,
                           profile=profile) # Pass profile for displaying existing images etc.

@bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            try:
                current_user.set_password(form.new_password.data)
                db.session.commit()
                flash('Your password has been updated!', 'success')
                # Log user out or redirect to dashboard? Redirecting for now.
                return redirect(url_for('player.dashboard'))
            except Exception as e:
                 db.session.rollback()
                 flash(f'Error changing password: {e}', 'danger')
        else:
            flash('Current password is incorrect.', 'danger')

    return render_template('player/change_password.html',
                           title='Change Password',
                           form=form)