from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user, login_required
from datetime import datetime

from app import db, socketio
from app.player import bp
from app.models import Registration, Tournament, TournamentCategory
from app.decorators import player_required

@bp.route('/check_in/<int:registration_id>', methods=['POST'])
@login_required
@player_required
def check_in(registration_id):
    """
    Allow a player to check in for their tournament registration.
    This marks them as present and ready to play.
    """
    registration = Registration.query.get_or_404(registration_id)
    profile = current_user.player_profile

    # Verify this registration belongs to the current user (as player 1 or 2)
    if not profile or (registration.player_id != profile.id and registration.partner_id != profile.id):
        flash('You do not have permission to check in for this registration.', 'danger')
        return redirect(url_for('player.my_registrations'))

    # Check if tournament is active (only allow check-in for active tournaments)
    tournament = registration.tournament
    if not tournament or tournament.status != 'ACTIVE':
        flash('Check-in is only available for active tournaments.', 'danger')
        return redirect(url_for('player.my_registrations'))

    # Check if already checked in
    if registration.checked_in:
        flash('You are already checked in for this registration.', 'info')
        return redirect(url_for('player.my_registrations'))

    try:
        # Update check-in status
        registration.checked_in = True
        registration.check_in_time = datetime.utcnow()
        db.session.commit()
        
        # Emit socket.io event for real-time updates
        socketio.emit('player_check_in', {
            'registration_id': registration.id,
            'player_name': profile.full_name,
            'category_name': registration.category.name,
            'tournament_id': tournament.id
        }, room=f'tournament_{tournament.id}')
        
        flash('Successfully checked in for the tournament.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error during check-in: {e}', 'danger')

    return redirect(url_for('player.my_registrations'))

@bp.route('/check_in_status/<int:tournament_id>')
@login_required
@player_required
def check_in_status(tournament_id):
    """
    Display check-in status for all of the player's registrations in a specific tournament.
    """
    tournament = Tournament.query.get_or_404(tournament_id)
    profile = current_user.player_profile
    
    if not profile:
        flash("Please create your player profile first.", "warning")
        return redirect(url_for('player.create_profile'))
    
    # Get all registrations for this player in this tournament
    registrations = Registration.query.join(TournamentCategory).filter(
        TournamentCategory.tournament_id == tournament_id,
        ((Registration.player_id == profile.id) | (Registration.partner_id == profile.id))
    ).all()
    
    if not registrations:
        flash("You don't have any registrations for this tournament.", "info")
        return redirect(url_for('player.my_registrations'))
    
    return render_template('player/check_in_status.html',
                           tournament=tournament,
                           registrations=registrations)

# API endpoint for AJAX check-in (optional alternative to form submission)
@bp.route('/api/check_in/<int:registration_id>', methods=['POST'])
@login_required
@player_required
def api_check_in(registration_id):
    registration = Registration.query.get_or_404(registration_id)
    profile = current_user.player_profile
    
    # Verify this registration belongs to the current user
    if not profile or (registration.player_id != profile.id and registration.partner_id != profile.id):
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    
    # Check if tournament is active
    tournament = registration.tournament
    if not tournament or tournament.status != 'ACTIVE':
        return jsonify({'success': False, 'message': 'Check-in only available for active tournaments'}), 400
    
    # Check if already checked in
    if registration.checked_in:
        return jsonify({'success': True, 'message': 'Already checked in', 'checked_in': True}), 200
    
    try:
        # Update check-in status
        registration.checked_in = True
        registration.check_in_time = datetime.utcnow()
        db.session.commit()
        
        # Emit socket.io event for real-time updates
        socketio.emit('player_check_in', {
            'registration_id': registration.id,
            'player_name': profile.full_name,
            'category_name': registration.category.name,
            'tournament_id': tournament.id
        }, room=f'tournament_{tournament.id}')
        
        return jsonify({
            'success': True, 
            'message': 'Successfully checked in',
            'checked_in': True,
            'check_in_time': registration.check_in_time.strftime("%Y-%m-%d %H:%M:%S")
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500
