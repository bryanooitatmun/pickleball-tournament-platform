from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user, login_required
from datetime import datetime
from flask_socketio import emit

from app import db, socketio
from app.organizer import bp # Import the blueprint
from app.models import (Tournament, TournamentCategory, Registration, User) # Use new import path
from app.decorators import organizer_required

@bp.route('/registrations')
@login_required
@organizer_required
def view_registrations():
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
    registrations_query = Registration.query.filter(Registration.category_id.in_(category_ids))

    # Filter by status if requested
    status_filter = request.args.get('status', 'pending')
    if status_filter == 'pending':
        # Show registrations with uploaded proof needing verification
        registrations_query = registrations_query.filter(
            Registration.payment_status == 'uploaded',
            Registration.payment_verified == False
        )
    elif status_filter == 'approved':
        registrations_query = registrations_query.filter(Registration.payment_verified == True)
    elif status_filter == 'rejected':
        registrations_query = registrations_query.filter(Registration.payment_status == 'rejected')
    elif status_filter == 'checked_in':
        # Add filter for checked-in players
        registrations_query = registrations_query.filter(
            Registration.checked_in == True
        )
    elif status_filter == 'not_checked_in':
        # Add filter for players who haven't checked in
        registrations_query = registrations_query.filter(
            Registration.payment_verified == True,  # Only approved registrations
            Registration.checked_in == False
        )
    elif status_filter == 'all':
        pass # No status filter

    # Filter by tournament if requested
    tournament_filter = request.args.get('tournament', 'all')
    if tournament_filter != 'all' and tournament_filter.isdigit():
        tournament_id = int(tournament_filter)
        # Ensure the selected tournament is one the user can access
        if tournament_id in tournament_ids:
            filtered_category_ids = [c.id for c in categories if c.tournament_id == tournament_id]
            registrations_query = registrations_query.filter(Registration.category_id.in_(filtered_category_ids))
        else:
             # If user tries to filter by a tournament they don't own/admin, show nothing or flash error
             registrations_query = registrations_query.filter(Registration.id == -1) # No results
             flash('You do not have permission to view registrations for the selected tournament.', 'warning')
    
    # Filter by category if requested
    category_filter = request.args.get('category', 'all')
    if category_filter != 'all' and category_filter.isdigit():
        category_id = int(category_filter)
        # Ensure the selected category is one the user can access
        if category_id in category_ids:
            registrations_query = registrations_query.filter(Registration.category_id == category_id)
        else:
            # If user tries to filter by a category they don't have access to, show nothing or flash error
            registrations_query = registrations_query.filter(Registration.id == -1)  # No results
            flash('You do not have permission to view registrations for the selected category.', 'warning')


    registrations = registrations_query.order_by(Registration.registration_date.desc()).all()

    return render_template('organizer/view_registrations.html',
                          title='Tournament Registrations',
                          registrations=registrations,
                          status_filter=status_filter,
                          tournament_filter=tournament_filter,
                          category_filter=category_filter,
                          all_tournaments=tournaments,
                          categories=categories) # Pass all accessible tournaments and categories for the filter dropdowns

@bp.route('/registration/<int:id>')
@login_required
@organizer_required
def view_registration(id):
    registration = Registration.query.get_or_404(id)
    # Ensure the tournament belongs to this organizer or user is admin
    tournament = registration.category.tournament
    if not current_user.is_admin() and tournament.organizer_id != current_user.id:
        flash('You do not have permission to view this registration.', 'danger')
        return redirect(url_for('organizer.view_registrations')) # Use correct endpoint name

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

    # Ensure the tournament belongs to this organizer or user is admin
    tournament = registration.category.tournament
    if not current_user.is_admin() and tournament.organizer_id != current_user.id:
        flash('You do not have permission to verify this registration.', 'danger')
        return redirect(url_for('organizer.view_registrations')) # Use correct endpoint name

    # Verify payment
    registration.payment_verified = True
    registration.payment_verified_at = datetime.utcnow()
    registration.payment_verified_by = current_user.id
    registration.payment_status = 'paid' # Mark as paid upon verification
    registration.is_approved = True # Also mark as approved
    registration.payment_rejection_reason = None # Clear any previous rejection reason

    try:
        db.session.commit()
        flash('Registration payment verified and approved!', 'success')
        # TODO: Optionally send confirmation email to player
    except Exception as e:
        db.session.rollback()
        flash(f'Error verifying registration: {e}', 'danger')

    return redirect(url_for('organizer.view_registration', id=id)) # Use correct endpoint name

@bp.route('/registration/<int:id>/reject', methods=['POST'])
@login_required
@organizer_required
def reject_registration(id):
    registration = Registration.query.get_or_404(id)

    # Ensure the tournament belongs to this organizer or user is admin
    tournament = registration.category.tournament
    if not current_user.is_admin() and tournament.organizer_id != current_user.id:
        flash('You do not have permission to reject this registration.', 'danger')
        return redirect(url_for('organizer.view_registrations')) # Use correct endpoint name

    # Get the rejection reason from form
    rejection_reason = request.form.get('rejection_reason', 'Payment proof rejected.') # Provide a default reason

    # Reject payment
    registration.payment_verified = False # Explicitly set to false
    registration.payment_verified_at = datetime.utcnow() # Record time of rejection check
    registration.payment_verified_by = current_user.id # Record who rejected
    registration.payment_status = 'rejected'
    registration.is_approved = False # Mark as not approved
    registration.payment_rejection_reason = rejection_reason

    try:
        db.session.commit()
        flash(f'Registration for {registration.team_name} has been rejected.', 'warning')
        # TODO: Optionally send rejection email to player with reason
    except Exception as e:
        db.session.rollback()
        flash(f'Error rejecting registration: {e}', 'danger')

    return redirect(url_for('organizer.view_registration', id=id)) # Use correct endpoint name

@bp.route('/registration/<int:id>/checkin', methods=['POST'])
@login_required
@organizer_required
def check_in_player(id):
    """
    Mark a player as checked in for their category
    """
    registration = Registration.query.get_or_404(id)

    # Ensure the tournament belongs to this organizer or user is admin
    tournament = registration.category.tournament
    if not current_user.is_admin() and tournament.organizer_id != current_user.id:
        flash('You do not have permission to check in this player.', 'danger')
        return redirect(url_for('organizer.view_registrations'))

    # Only approved registrations can be checked in
    if not registration.payment_verified:
        flash('Only approved registrations can be checked in.', 'warning')
        return redirect(url_for('organizer.view_registration', id=id))

    # Check in the player
    registration.checked_in = True
    registration.check_in_time = datetime.utcnow()

    try:
        db.session.commit()
        flash(f'{registration.team_name} has been checked in.', 'success')
        
        # Emit socket event for real-time updates
        tournament_id = registration.category.tournament_id
        socketio.emit('player_checked_in', {
            'registration_id': registration.id,
            'player_name': registration.team_name,
            'category_id': registration.category_id,
            'check_in_time': registration.check_in_time.isoformat() if registration.check_in_time else None
        }, room=f'tournament_{tournament_id}')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error checking in player: {e}', 'danger')

    return redirect(url_for('organizer.view_registration', id=id))

@bp.route('/registration/<int:id>/checkout', methods=['POST'])
@login_required
@organizer_required
def check_out_player(id):
    """
    Remove a player's check-in status
    """
    registration = Registration.query.get_or_404(id)

    # Ensure the tournament belongs to this organizer or user is admin
    tournament = registration.category.tournament
    if not current_user.is_admin() and tournament.organizer_id != current_user.id:
        flash('You do not have permission to check out this player.', 'danger')
        return redirect(url_for('organizer.view_registrations'))

    # Remove check-in
    registration.checked_in = False
    registration.check_in_time = None

    try:
        db.session.commit()
        flash(f'{registration.team_name} has been checked out.', 'success')
        
        # Emit socket event for real-time updates
        tournament_id = registration.category.tournament_id
        socketio.emit('player_checked_out', {
            'registration_id': registration.id,
            'player_name': registration.team_name,
            'category_id': registration.category_id
        }, room=f'tournament_{tournament_id}')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error checking out player: {e}', 'danger')

    return redirect(url_for('organizer.view_registration', id=id))

@bp.route('/tournament/<int:id>/category/<int:category_id>/check-in-status')
@login_required
@organizer_required
def category_check_in_status(id, category_id):
    """
    API endpoint to get check-in status for all players in a category
    """
    tournament = Tournament.query.get_or_404(id)
    category = TournamentCategory.query.get_or_404(category_id)
    
    # Ensure the tournament belongs to this organizer or user is admin
    if not current_user.is_admin() and tournament.organizer_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
        
    # Ensure category belongs to the tournament
    if category.tournament_id != tournament.id:
        return jsonify({'error': 'Category does not belong to this tournament'}), 400
        
    # Get all approved registrations for this category
    registrations = Registration.query.filter_by(
        category_id=category_id,
        payment_verified=True
    ).all()
    
    # Format registration data
    registration_data = []
    for reg in registrations:
        reg_info = {
            'id': reg.id,
            'team_name': reg.team_name,
            'checked_in': reg.checked_in,
            'check_in_time': reg.check_in_time.isoformat() if reg.check_in_time else None
        }
        registration_data.append(reg_info)
    
    return jsonify({
        'category_id': category_id,
        'category_name': category.name,
        'tournament_id': tournament.id,
        'tournament_name': tournament.name,
        'registrations': registration_data,
        'total_count': len(registration_data),
        'checked_in_count': sum(1 for reg in registration_data if reg['checked_in'])
    })