from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user, login_required
from flask_socketio import emit
from datetime import datetime

from app import db, socketio
from app.player import bp  # Import the blueprint
from app.models import Match, Tournament, TournamentCategory, PlayerProfile, Team
from app.helpers.tournament import _format_match_for_api

@bp.route('/match/<int:match_id>/verify', methods=['POST'])
@login_required
def verify_match(match_id):
    """
    Allows a player to verify the match result. 
    Only the captain (typically player1) can verify for a team.
    """
    match = Match.query.get_or_404(match_id)
    profile = current_user.player_profile
    
    if not profile:
        flash('You need a player profile to verify match results.', 'danger')
        return redirect(url_for('tournament.match_detail', id=match.category.tournament_id, match_id=match_id))
    
    #Make sure match has a referee verification first
    if not match.referee_verified:
        flash('This match must be verified by a referee before player verification.', 'danger')
        return redirect(url_for('tournament.match_detail', id=match.category.tournament_id, match_id=match_id))
    
    # Make sure match has scores and is marked as completed
    # if not match.completed or match.scores.count() == 0:
    #     flash('Match must be completed with scores before verification.', 'danger')
    #     return redirect(url_for('tournament.match_detail', id=match.category.tournament_id, match_id=match_id))

    # Make sure match has scores 
    if match.scores.count() == 0:
        flash('Match must be completed with scores before verification.', 'danger')
        return redirect(url_for('tournament.match_detail', id=match.category.tournament_id, match_id=match_id))
    
    # Check if the current user is a player in this match
    is_authorized = False
    
    if match.is_doubles:
        # For doubles, check if player is in either team
        # For verification, typically only team captain (player1) should verify
        if (match.team1_id and match.team1_profile and 
            (match.team1_profile.player1_id == profile.id)):
            is_authorized = True
        elif (match.team2_id and match.team2_profile and 
              (match.team2_profile.player1_id == profile.id)):
            is_authorized = True
    else:
        # For singles, either player can verify
        if match.player1_id == profile.id or match.player2_id == profile.id:
            is_authorized = True
    
    if not is_authorized:
        flash('You are not authorized to verify this match.', 'danger')
        return redirect(url_for('tournament.match_detail', id=match.category.tournament_id, match_id=match_id))
    
    # Digital signature verification if enabled
    signature = request.form.get('digital_signature')
    if current_user.digital_signature_hash and signature:
        if not current_user.verify_digital_signature(signature):
            flash('Invalid digital signature. Please try again.', 'danger')
            return redirect(url_for('tournament.match_detail', id=match.category.tournament_id, match_id=match_id))
    
    try:
        # Update match verification status
        match.player_verified = True
        match.completed = True
        db.session.commit()
        
        # Emit socket.io event for real-time updates
        socketio.emit('match_updated', {
            'match': _format_match_for_api(match),
            'tournament_id': match.category.tournament_id,
            'category_id': match.category_id
        }, room=f'tournament_{match.category.tournament_id}')
        
        flash('Match result successfully verified.', 'success')
        
        # If next match is available and both referee and player verified, update bracket
        # if match.next_match_id and match.referee_verified and match.player_verified:
        #     from app.services import BracketService
        #     BracketService.advance_winner(match)
        #     flash('Winner has been advanced to the next round.', 'info')
            
    except Exception as e:
        db.session.rollback()
        flash(f'Error verifying match: {e}', 'danger')
    
    return redirect(url_for('tournament.match_detail', id=match.category.tournament_id, match_id=match_id))

@bp.route('/api/next_match')
@login_required
def get_next_match():
    """API endpoint to get the player's next upcoming match for the persistent match bar"""
    if not current_user.player_profile:
        return jsonify({'error': 'No player profile found'}), 404
    
    profile_id = current_user.player_profile.id
    
    # Find the next scheduled match where this player is participating
    # Start with singles matches
    next_match = Match.query.filter(
        ((Match.player1_id == profile_id) | (Match.player2_id == profile_id)),
        Match.scheduled_time > datetime.utcnow(),
        Match.completed == False
    ).order_by(Match.scheduled_time).first()
    
    # If no singles match found, check doubles
    if not next_match:
        # This query is more complex as we need to check team memberships
        # We'll use joins for this
        team_matches = Match.query.join(
            Team, 
            ((Match.team1_id == Team.id) | (Match.team2_id == Team.id))
        ).filter(
            ((Team.player1_id == profile_id) | (Team.player2_id == profile_id)),
            Match.scheduled_time > datetime.utcnow(),
            Match.completed == False
        ).order_by(Match.scheduled_time).first()
        
        next_match = team_matches
    
    if not next_match:
        return jsonify({'message': 'No upcoming matches found'}), 404
    
    # Format the match data for the API response
    match_data = {
        'id': next_match.id,
        'tournament_id': next_match.category.tournament_id,
        'tournament_name': next_match.category.tournament.name,
        'category_name': next_match.category.name,
        'scheduled_time': next_match.scheduled_time.strftime('%Y-%m-%d %H:%M') if next_match.scheduled_time else None,
        'court': next_match.court,
        'opponent': None
    }
    
    # Determine the opponent
    if next_match.is_doubles:
        if next_match.team1 and next_match.team1.player1_id == profile_id or next_match.team1.player2_id == profile_id:
            if next_match.team2:
                match_data['opponent'] = f"{next_match.team2.player1.full_name}/{next_match.team2.player2.full_name}"
        else:
            if next_match.team1:
                match_data['opponent'] = f"{next_match.team1.player1.full_name}/{next_match.team1.player2.full_name}"
    else:
        if next_match.player1_id == profile_id:
            if next_match.player2:
                match_data['opponent'] = next_match.player2.full_name
        else:
            if next_match.player1:
                match_data['opponent'] = next_match.player1.full_name
    
    return jsonify(match_data)
