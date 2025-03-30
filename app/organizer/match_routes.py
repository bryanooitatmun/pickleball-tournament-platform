from flask import render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import current_user, login_required
from datetime import datetime
from flask_socketio import emit

from app import db, socketio
from app.organizer import bp # Import the blueprint
# Import necessary models using the new structure
from app.models import Tournament, TournamentCategory, Match, MatchScore, TournamentStatus, TournamentFormat, Registration
from app.decorators import organizer_required, referee_required, referee_or_organizer_required
# Import services or helpers needed for bracket generation, placing, etc.
from app.services import BracketService, PlacingService
from app.helpers.tournament import (
    _generate_group_stage,
    _generate_knockout_from_groups,
    _generate_single_elimination,
    _format_match_for_api,
    update_match_seeds
)
# Import forms
from app.organizer.forms import MatchForm, ScoreForm, CompleteMatchForm

# --- Match Management ---

@bp.route('/tournament/<int:id>/update_match/<int:match_id>', methods=['GET', 'POST'])
@login_required
@referee_or_organizer_required # Allows Referees, Organizers, and Admins (via is_organizer check)
def update_match(id, match_id):
    """Update match scores and potentially winner based on form submission."""
    tournament = Tournament.query.get_or_404(id)
    match = Match.query.get_or_404(match_id)
    form = MatchForm()

    # Permission check is now handled by the decorator above

    if match.category.tournament_id != tournament.id:
         flash('Match does not belong to this tournament.', 'danger')
         return redirect(url_for('organizer.tournament_detail', id=id))

    if request.method == 'GET':
        # Populate form with existing data for GET request
        form.court.data = match.court
        if match.scheduled_time:
            form.scheduled_time.data = match.scheduled_time
        form.livestream_url.data = match.livestream_url
        
        # Populate score form fields based on existing scores
        existing_scores = match.scores.all()
        form.set_count.data = len(existing_scores)
        
        for i, score in enumerate(existing_scores):
            if i < len(form.scores):
                form.scores[i].player1_score.data = score.player1_score
                form.scores[i].player2_score.data = score.player2_score
        
        return render_template('organizer/edit_match.html', 
                              title=f"Edit Match",
                              tournament=tournament,
                              match=match,
                              form=form)

    if form.validate_on_submit():
        try:
            # --- Update Scheduling Info ---
            old_court = match.court
            old_time = match.scheduled_time
            old_livestream = match.livestream_url
            
            match.court = form.court.data
            match.scheduled_time = form.scheduled_time.data
            match.livestream_url = form.livestream_url.data
            
            # Check if scheduling changed for notification purposes
            schedule_changed = (old_court != match.court or 
                               old_time != match.scheduled_time or
                               old_livestream != match.livestream_url)

            if schedule_changed:
                # Track what changed for notification
                changes = {}
                if old_court != match.court:
                    changes['court'] = match.court
                if old_time != match.scheduled_time:
                    changes['scheduled_time'] = match.scheduled_time
                if old_livestream != match.livestream_url:
                    changes['livestream_url'] = match.livestream_url
                
                # Schedule notification task
                from app.tasks.email_tasks import send_schedule_change_email
                send_schedule_change_email(match.id, changes)
                
            # --- Update Scores ---
            set_count = form.set_count.data
            new_scores = []
            player1_sets_won = 0
            player2_sets_won = 0

            # Clear existing scores for this match before adding new ones
            MatchScore.query.filter_by(match_id=match_id).delete()

            for i in range(set_count):
                if i < len(form.scores):
                    p1_score = form.scores[i].player1_score.data
                    p2_score = form.scores[i].player2_score.data
                    
                    score = MatchScore(
                        match_id=match_id,
                        set_number=i+1,
                        player1_score=p1_score,
                        player2_score=p2_score
                    )
                    new_scores.append(score)
                    db.session.add(score)

                    # Track set winner
                    if p1_score > p2_score:
                        player1_sets_won += 1
                    elif p2_score > p1_score:
                        player2_sets_won += 1

            # --- Determine Winner (if scores provided allow) ---
            winner_determined = False
            if player1_sets_won > player2_sets_won:
                 # Player 1 / Team 1 wins
                 if match.is_doubles:
                     match.winning_team_id = match.team1_id
                     match.losing_team_id = match.team2_id
                     match.winning_player_id = None
                     match.losing_player_id = None
                 else:
                     match.winning_player_id = match.player1_id
                     match.losing_player_id = match.player2_id
                     match.winning_team_id = None
                     match.losing_team_id = None
                 match.completed = True
                 winner_determined = True
            elif player2_sets_won > player1_sets_won:
                 # Player 2 / Team 2 wins
                 if match.is_doubles:
                     match.winning_team_id = match.team2_id
                     match.losing_team_id = match.team1_id
                     match.winning_player_id = None
                     match.losing_player_id = None
                 else:
                     match.winning_player_id = match.player2_id
                     match.losing_player_id = match.player1_id
                     match.winning_team_id = None
                     match.losing_team_id = None
                 match.completed = True
                 winner_determined = True
            else:
                 # Scores might be incomplete or a draw (if allowed)
                 match.completed = False
                 match.winning_player_id = None
                 match.winning_team_id = None
                 match.losing_player_id = None
                 match.losing_team_id = None

            # --- Verification ---
            # Set referee verification based on current user role
            if current_user.role == 'REFEREE':
                match.referee_verified = True
            elif current_user.role == 'ORGANIZER' or current_user.role == 'ADMIN':
                # Organizers can set both verifications
                match.referee_verified = form.referee_verified.data
                match.player_verified = form.player_verified.data

            # --- Commit Changes ---
            db.session.commit()

            # --- Post-Commit Actions ---
            # Emit socket.io event with match update
            # --- Emit socket.io events with match update
            socketio.emit('match_update', {
                'match': _format_match_for_api(match),
                'tournament_id': match.category.tournament_id,
                'category_id': match.category_id,
                'status': 'completed' if match.completed else 'in_progress'
            }, room=f'tournament_{match.category.tournament_id}')
            
            # Emit score update for live match view
            socketio.emit('score_update', {
                'match_id': match.id,
                'player1_score': new_scores[-1].player1_score if new_scores else 0,
                'player2_score': new_scores[-1].player2_score if new_scores else 0,
                'set_number': len(new_scores)
            }, room=f'match_{match.id}')
            
            # Emit court update for live courts view
            if match.court:
                socketio.emit('court_update', {
                    'court': match.court,
                    'match_id': match.id,
                    'tournament_id': match.category.tournament_id,
                    'status': 'completed' if match.completed else 'in_progress'
                }, room=f'courts_view_{match.category.tournament_id}')

            # Schedule notification for court/time change if needed
            if schedule_changed:
                # Track what changed for notification
                changes = {}
                if old_court != match.court:
                    changes['court'] = match.court
                if old_time != match.scheduled_time:
                    changes['scheduled_time'] = match.scheduled_time.strftime('%Y-%m-%d %H:%M') if match.scheduled_time else None
                
                # Schedule notification task (this would be implemented in tasks.py)
                from app.tasks.email_tasks import send_schedule_change_email
                send_schedule_change_email(match.id, changes)

            # If winner determined, update standings/brackets
            if winner_determined:
                # If this is a group match, update group standings
                if match.group_id:
                    BracketService.update_group_standings(match.group_id)

                # If knockout, advance winner to next match
                elif match.next_match_id:
                     BracketService.advance_winner(match)

            flash('Match updated successfully.', 'success')
            return redirect(url_for('organizer.manage_category', id=id, category_id=match.category_id))

        except ValueError as e:
             db.session.rollback()
             flash(f'Invalid input: {e}', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating match: {e}', 'danger')

    # If form validation failed
    return render_template('organizer/edit_match.html', 
                          title=f"Edit Match",
                          tournament=tournament,
                          match=match,
                          form=form)


# --- Bracket & Placing Routes ---

@bp.route('/tournament/<int:id>/generate_all_brackets', methods=['POST'])
@login_required
@organizer_required
def generate_all_brackets(id):
    """Generate brackets for all categories in a tournament"""
    tournament = Tournament.query.get_or_404(id)

    # Check permission
    if not current_user.is_admin() and tournament.organizer_id != current_user.id:
        flash('You do not have permission to generate brackets for this tournament.', 'danger')
        return redirect(url_for('organizer.tournament_detail', id=id))

    if tournament.status != TournamentStatus.UPCOMING:
         flash('Brackets can only be generated for upcoming tournaments.', 'warning')
         return redirect(url_for('organizer.tournament_detail', id=id))

    success_count = 0
    fail_count = 0
    skipped_count = 0
    try:
        for category in tournament.categories:
            # Check if brackets already exist for this category
            if Match.query.filter_by(category_id=category.id).count() > 0:
                 current_app.logger.info(f"Skipping bracket generation for category {category.id} - matches already exist.")
                 skipped_count += 1
                 continue

            category_format = category.format or tournament.format # Use category format override if available
            success = False
            use_seeding = True  # Default to use seeding
            third_place_match = True  # Default to include 3rd place match
            
            if category_format == TournamentFormat.GROUP_KNOCKOUT:
                # Requires group stage generation first
                success = _generate_group_stage(category)
                if success:
                     current_app.logger.info(f"Generated group stage for category {category.id}")
                else:
                     current_app.logger.error(f"Failed to generate group stage for category {category.id}")

            elif category_format == TournamentFormat.SINGLE_ELIMINATION:
                success = _generate_single_elimination(category, use_seeding, third_place_match)
                
            # Add support for other formats as needed
            else:
                 current_app.logger.warning(f"Bracket generation not implemented for format {category_format.value} in category {category.id}")

            if success:
                success_count += 1
            else:
                fail_count += 1

        # Commit all generated matches (if helpers don't commit individually)
        db.session.commit()
        flash_message = f"Bracket generation attempted: {success_count} succeeded, {fail_count} failed, {skipped_count} skipped (already exist)."
        flash(flash_message, 'success' if fail_count == 0 else 'warning')

    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred during bracket generation: {e}', 'danger')

    return redirect(url_for('organizer.tournament_detail', id=id))

@bp.route('/tournament/<int:id>/category/<int:category_id>/update_seeds', methods=['POST'])
@login_required
@organizer_required
def update_seeds(id, category_id):
    """Update seeding for registrations in a category"""
    tournament = Tournament.query.get_or_404(id)
    category = TournamentCategory.query.get_or_404(category_id)
    
    # Permission check
    if not current_user.is_admin() and tournament.organizer_id != current_user.id:
        flash('You do not have permission to update seeds for this tournament.', 'danger')
        return redirect(url_for('organizer.tournament_detail', id=id))
        
    if category.tournament_id != tournament.id:
        flash('Category does not belong to this tournament.', 'danger')
        return redirect(url_for('organizer.tournament_detail', id=id))
    
    # Extract seed data from form
    seed_data = {}
    for key, value in request.form.items():
        if key.startswith('seed_'):
            reg_id = key.replace('seed_', '')
            seed_data[reg_id] = value if value.strip() else None
    
    success = update_match_seeds(category_id, seed_data)
    
    if success:
        flash('Seeding updated successfully.', 'success')
    else:
        flash('Error updating seeding.', 'danger')
    
    return redirect(url_for('organizer.manage_category', id=id, category_id=category_id))

@bp.route('/tournament/<int:id>/category/<int:category_id>/generate_bracket', methods=['POST'])
@login_required
@organizer_required
def generate_bracket(id, category_id):
    """Generate bracket for a specific category with options"""
    tournament = Tournament.query.get_or_404(id)
    category = TournamentCategory.query.get_or_404(category_id)
    
    # Permission check
    if not current_user.is_admin() and tournament.organizer_id != current_user.id:
        flash('You do not have permission to generate brackets for this tournament.', 'danger')
        return redirect(url_for('organizer.tournament_detail', id=id))
        
    if category.tournament_id != tournament.id:
        flash('Category does not belong to this tournament.', 'danger')
        return redirect(url_for('organizer.tournament_detail', id=id))
    
    # Get bracket options from form
    bracket_type = request.form.get('bracket_type')
    use_seeding = request.form.get('use_seeding') == 'on'
    third_place_match = request.form.get('third_place_match') == 'on'
    
    try:
        success = False
        message = "Bracket generation failed."
        
        if bracket_type == 'generate_groups' and category.format == TournamentFormat.GROUP_KNOCKOUT:
            success = _generate_group_stage(category)
            message = 'Group stage generated successfully.' if success else 'Failed to generate group stage.'
            
        elif bracket_type == 'generate_knockout':
            if category.format == TournamentFormat.GROUP_KNOCKOUT:
                success = _generate_knockout_from_groups(category)
                message = 'Knockout bracket generated from groups successfully.' if success else 'Failed to generate knockout from groups.'
                
            elif category.format == TournamentFormat.SINGLE_ELIMINATION:
                success = _generate_single_elimination(category, use_seeding, third_place_match)
                message = 'Single elimination bracket generated successfully.' if success else 'Failed to generate single elimination bracket.'
                
            # Add support for other formats as needed
            else:
                message = f"Bracket generation not applicable for format: {category.format.value}"
                
        else:
            message = 'Invalid bracket type or format mismatch.'
        
        flash(message, 'success' if success else 'danger')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error during bracket generation: {e}', 'danger')
    
    return redirect(url_for('organizer.manage_category', id=id, category_id=category_id))

@bp.route('/tournament/<int:id>/calculate_placings/<int:category_id>', methods=['POST'])
@login_required
@organizer_required
def calculate_placings(id, category_id):
    """Calculate final placings for a category after all matches are complete."""
    tournament = Tournament.query.get_or_404(id)
    category = TournamentCategory.query.get_or_404(category_id)

    # Permission check
    if not current_user.is_admin() and tournament.organizer_id != current_user.id:
        flash('You do not have permission to calculate placings for this tournament.', 'danger')
        return redirect(url_for('organizer.tournament_detail', id=id))
    if category.tournament_id != tournament.id:
         flash('Category does not belong to this tournament.', 'danger')
         return redirect(url_for('organizer.tournament_detail', id=id))

    # Ensure tournament/category is completed or ready for placing calculation
    # Check if all matches in the category are completed
    incomplete_matches = Match.query.filter_by(category_id=category_id, completed=False).count()
    if incomplete_matches > 0:
        flash(f'Cannot calculate placings: {incomplete_matches} matches in this category are not yet completed.', 'warning')
        return redirect(url_for('organizer.manage_category', id=id, category_id=category_id))

    try:
        # Use PlacingService to calculate and potentially store placings
        # This service would contain the logic based on bracket results
        placings = PlacingService.calculate_and_store_placings(category_id) # Assumes service exists and returns/stores results

        # Award points based on placings and category settings
        points_awarded = PlacingService.award_points(category_id, placings)

        flash(f'Calculated {len(placings)} placings for category {category.name}. Points awarded.', 'success')
    except Exception as e:
        flash(f'Error calculating placings: {e}', 'danger')
        # No rollback needed usually for calculation, unless it tries to store results

    # Redirect to results page or category management
    return redirect(url_for('organizer.manage_category', id=id, category_id=category_id))