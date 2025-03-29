from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user, login_required
from datetime import datetime

from app import db
from app.organizer import bp # Import the blueprint
# Import necessary models using the new structure
from app.models import Tournament, TournamentCategory, Match, MatchScore, TournamentStatus, TournamentFormat
from app.decorators import organizer_required
# Import services or helpers needed for bracket generation, placing, etc.
from app.services import BracketService, PlacingService
from app.helpers.tournament import (
    _generate_group_stage,
    _generate_knockout_from_groups,
    _generate_single_elimination
)
# Import forms if needed (e.g., for manual match editing if added later)
# from app.organizer.forms import MatchForm, ScoreForm, CompleteMatchForm

# --- Match Management ---

@bp.route('/tournament/<int:id>/update_match/<int:match_id>', methods=['POST'])
@login_required
@organizer_required # Or maybe referee_required as well?
def update_match(id, match_id):
    """Update match scores and potentially winner based on form submission."""
    tournament = Tournament.query.get_or_404(id)
    match = Match.query.get_or_404(match_id)

    # Permission check
    if not current_user.is_admin() and tournament.organizer_id != current_user.id:
        # Add check for referee role if applicable
        flash('You do not have permission to update matches for this tournament.', 'danger')
        # Redirect likely needs context, maybe back to bracket view or manage_category
        return redirect(url_for('organizer.tournament_detail', id=id))

    if match.category.tournament_id != tournament.id:
         flash('Match does not belong to this tournament.', 'danger')
         return redirect(url_for('organizer.tournament_detail', id=id))

    try:
        # --- Update Scores ---
        set_count = int(request.form.get('set_count', 0))
        new_scores = []
        player1_sets_won = 0
        player2_sets_won = 0

        # Clear existing scores for this match before adding new ones
        MatchScore.query.filter_by(match_id=match_id).delete()

        for i in range(1, set_count + 1):
            p1_score_str = request.form.get(f'player1_score_{i}', '')
            p2_score_str = request.form.get(f'player2_score_{i}', '')

            # Basic validation: ensure scores are integers if provided
            if p1_score_str or p2_score_str: # Only process if at least one score is entered for the set
                p1_score = int(p1_score_str or 0)
                p2_score = int(p2_score_str or 0)
                if p1_score < 0 or p2_score < 0:
                     raise ValueError("Scores cannot be negative.")

                score = MatchScore(
                    match_id=match_id,
                    set_number=i,
                    player1_score=p1_score,
                    player2_score=p2_score
                )
                new_scores.append(score)
                db.session.add(score) # Add to session

                # Track set winner (simple win-by-points, adjust for tie-breaks if needed)
                if p1_score > p2_score:
                    player1_sets_won += 1
                elif p2_score > p1_score:
                    player2_sets_won += 1

        # --- Determine Winner (if scores provided allow) ---
        # This logic assumes a best-of-N sets scenario based on scores entered
        # It might need adjustment based on specific game rules (e.g., win by 2)
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
             match.completed = False # Mark as incomplete if winner cannot be determined
             match.winning_player_id = None
             match.winning_team_id = None
             match.losing_player_id = None
             match.losing_team_id = None


        # --- Update Scheduling Info ---
        match.court = request.form.get('court', match.court) # Update court if provided
        scheduled_time_str = request.form.get('scheduled_time')
        if scheduled_time_str:
            try:
                # Adjust format string as needed based on input type (e.g., datetime-local)
                match.scheduled_time = datetime.strptime(scheduled_time_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                 flash('Invalid format for scheduled time.', 'warning')
                 # Keep existing time or set to None? Decide policy.


        # --- Verification (Placeholder - Requires Player/Referee interaction) ---
        # For now, assume organizer update implies verification
        match.referee_verified = True # Or based on current_user.role == 'referee'
        match.player_verified = True # Needs separate mechanism for player verification


        # --- Commit Changes ---
        db.session.commit()

        # --- Post-Commit Actions (Advancement, Standings) ---
        if winner_determined:
            # If this is a group match, update group standings
            if match.group_id:
                BracketService.update_group_standings(match.group_id) # Assumes service exists

            # If knockout, advance winner to next match
            elif match.next_match_id:
                 BracketService.advance_winner(match) # Assumes service exists

        flash('Match updated successfully.', 'success')

    except ValueError as e:
         db.session.rollback()
         flash(f'Invalid score input: {e}', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating match: {e}', 'danger')

    # Redirect back to the category management page where matches are often displayed
    return redirect(url_for('organizer.manage_category', id=id, category_id=match.category_id))


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
            if category_format == TournamentFormat.GROUP_KNOCKOUT:
                # Requires group stage generation first, then knockout from groups
                # This might need a multi-step process or more complex logic
                # For now, just attempt group stage generation as an example
                success = _generate_group_stage(category) # Assumes helper exists
                if success:
                     # Ideally, knockout generation happens after group stage is played
                     # For now, just log success of group stage part
                     current_app.logger.info(f"Generated group stage for category {category.id}")
                else:
                     current_app.logger.error(f"Failed to generate group stage for category {category.id}")

            elif category_format == TournamentFormat.SINGLE_ELIMINATION:
                # TODO: Get seeding/3rd place options if needed
                success = _generate_single_elimination(category) # Assumes helper exists
            # Add elif for ROUND_ROBIN, DOUBLE_ELIMINATION etc.
            # elif category_format == TournamentFormat.ROUND_ROBIN:
            #     success = _create_round_robin_matches(category) # Assumes helper exists

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

        # TODO: Award points based on placings and category settings
        # points_awarded = PlacingService.award_points(category_id, placings)

        flash(f'Calculated {len(placings)} placings for category {category.name}. Points awarded.', 'success') # Adjust message
    except Exception as e:
        flash(f'Error calculating placings: {e}', 'danger')
        # No rollback needed usually for calculation, unless it tries to store results

    # Redirect to results page or category management
    # return redirect(url_for('main.results', id=id, category_id=category_id)) # Example redirect to a results view
    return redirect(url_for('organizer.manage_category', id=id, category_id=category_id))