from flask import render_template, redirect, url_for, flash
from flask_login import current_user, login_required
from datetime import datetime
import json

from app import db # Might not be needed if only reading
from app.player import bp # Import the blueprint
# Import necessary models using the new structure
from app.models import PlayerProfile, Registration, TournamentStatus, TournamentCategory, Match, Team


@bp.route('/dashboard')
@login_required
def dashboard():
    # Get player profile or redirect to create profile if none exists
    profile = current_user.player_profile # Assumes relationship is loaded via user_loader
    if not profile:
        flash('Please complete your player profile first.', 'warning')
        return redirect(url_for('player.create_profile'))

    # Get registrations where user is player1 or player2
    # Eager load related data to avoid N+1 queries in template/loop
    registrations = Registration.query.options(
        db.joinedload(Registration.category).joinedload(TournamentCategory.tournament) # Load Tournament via TournamentCategory
    ).filter(
        (Registration.player_id == profile.id) | (Registration.partner_id == profile.id)
    ).all()

    # Prepare data structures for the dashboard
    upcoming_tournaments_data = []
    ongoing_tournaments_data = []
    past_tournaments_data = []

    # Stats to display
    stats = {
        'total_tournaments': 0,
        'completed_tournaments': 0,
        'upcoming_tournaments': 0,
        'pending_payments': 0,
        'rejected_payments': 0,
        # Add more stats if needed (e.g., win/loss, points)
        'total_points': profile.get_points(None), # Example: Get total points across all categories (needs refinement in model)
        # Add enhanced statistics
        'matches_won': profile.matches_won,
        'matches_lost': profile.matches_lost,
        'win_loss_ratio': round(profile.matches_won / (profile.matches_won + profile.matches_lost) * 100, 1) if (profile.matches_won + profile.matches_lost) > 0 else 0,
        'avg_match_duration': profile.avg_match_duration or 0
    }

    # Group registrations by tournament
    tournament_reg_map = {}
    for reg in registrations:
        # Skip if category or tournament data is missing (shouldn't happen with joinedload)
        if not reg.category or not reg.tournament:
            continue

        tournament = reg.tournament
        tournament_id = tournament.id

        if tournament_id not in tournament_reg_map:
            tournament_reg_map[tournament_id] = {
                'tournament': tournament,
                'registrations': []
            }
        tournament_reg_map[tournament_id]['registrations'].append(reg)

        # Count payment statuses relevant to the player
        if reg.payment_status == 'uploaded' and not reg.payment_verified:
             # Only count if this user is player 1 (usually responsible for payment)
             if reg.player_id == profile.id:
                 stats['pending_payments'] += 1
        elif reg.payment_status == 'rejected':
             if reg.player_id == profile.id:
                 stats['rejected_payments'] += 1

    # Process grouped data
    for tournament_id, data in tournament_reg_map.items():
        tournament = data['tournament']

        # --- Placeholder for calculating results/placings ---
        # This logic is complex and likely belongs in a service or needs efficient querying
        # The current placeholder iterates winners_by_category which might be inefficient
        tournament_results = []
        if tournament.status == TournamentStatus.COMPLETED:
            stats['completed_tournaments'] += 1
            # Example: Fetch pre-calculated results if available, or run calculation here (less ideal)
            # for reg in data['registrations']:
            #     category = reg.category
            #     # Query Match results or a dedicated Result table for this player/category
            #     # Placeholder:
            #     result = {'category': category.name, 'place': 'N/A', 'points': 0}
            #     tournament_results.append(result)
            data['results'] = tournament_results # Attach results
            past_tournaments_data.append(data)

        elif tournament.status == TournamentStatus.ONGOING:
            ongoing_tournaments_data.append(data)
        else: # UPCOMING
            upcoming_tournaments_data.append(data)
            stats['upcoming_tournaments'] += 1

    # Get match history
    # Singles matches where player is player1 or player2
    singles_matches = Match.query.filter(
        (Match.player1_id == profile.id) | (Match.player2_id == profile.id),
        Match.is_doubles == False
    ).order_by(Match.scheduled_time.desc()).limit(10).all()
    
    # Doubles matches where player is in team1 or team2
    # First find all teams that include the player
    player_teams = Team.query.filter(
        db.or_(
            Team.player1_id == profile.id,
            Team.player2_id == profile.id
        )
    ).all()

    team_ids = [team.id for team in player_teams]

    # Find matches where these teams participate (either as team1 or team2)
    doubles_matches = Match.query.filter(
        db.or_(
            Match.team1_id.in_(team_ids),
            Match.team2_id.in_(team_ids)
        )
    ).order_by(Match.scheduled_time.desc()).limit(10).all()
    
    # Combine and sort by date
    match_history = singles_matches + doubles_matches
    match_history.sort(key=lambda x: x.scheduled_time or datetime.min, reverse=True)
    match_history = match_history[:10]  # Limit to most recent 10

    # Sort tournaments by date
    upcoming_tournaments_data.sort(key=lambda x: x['tournament'].start_date or datetime.min)
    ongoing_tournaments_data.sort(key=lambda x: x['tournament'].start_date or datetime.min)
    past_tournaments_data.sort(key=lambda x: x['tournament'].end_date or datetime.min, reverse=True)

    # Set total tournaments count
    stats['total_tournaments'] = len(tournament_reg_map)
    
    # Next upcoming match
    # Singles matches
    singles_match = Match.query.filter(
        db.or_(Match.player1_id == profile.id, Match.player2_id == profile.id),
        Match.scheduled_time > datetime.utcnow(),
        Match.completed == False
    ).order_by(Match.scheduled_time).first()

    # Doubles matches
    doubles_match = Match.query.join(
        Team, 
        ((Match.team1_id == Team.id) | (Match.team2_id == Team.id))
    ).filter(
        ((Team.player1_id == profile.id) | (Team.player2_id == profile.id)),
        Match.scheduled_time > datetime.utcnow(),
        Match.completed == False
    ).order_by(Match.scheduled_time).first()

    # Compare and select the earlier match
    if singles_match and doubles_match:
        next_match = singles_match if singles_match.scheduled_time <= doubles_match.scheduled_time else doubles_match
    elif singles_match:
        next_match = singles_match
    else:
        next_match = doubles_match

    return render_template('player/dashboard.html',
                           title='Player Dashboard',
                           profile=profile,
                           upcoming_tournaments=upcoming_tournaments_data,
                           ongoing_tournaments=ongoing_tournaments_data,
                           past_tournaments=past_tournaments_data,
                           stats=stats,
                           match_history=match_history,
                           next_match=next_match)