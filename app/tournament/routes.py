from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user, login_required
from app import db
from app.tournament import bp
from app.models import Tournament, TournamentCategory, Match, MatchScore, Registration, PlayerProfile, TournamentStatus, CategoryType, Team, TournamentFormat
from app.services import BracketService, PlacingService, PrizeService, RegistrationService
from datetime import datetime
from app.helpers.tournament import _format_match_for_api

@bp.route('/<int:id>/bracket')
def bracket(id):
    """
    Enhanced bracket view with support for group stages and knockout formats
    """
    # Get tournament
    tournament = Tournament.query.get_or_404(id)
    
    # Get all categories for this tournament
    categories = tournament.categories.all()
    if not categories:
        flash('No categories found for this tournament.', 'warning')
        return redirect(url_for('main.tournament_detail', id=id))
    
    # Get selected category (default to first category)
    category_id = request.args.get('category', type=int) or categories[0].id
    selected_category = TournamentCategory.query.get_or_404(category_id)
    
    # Use BracketService to get comprehensive bracket data
    bracket_data = BracketService.get_bracket_data(category_id)

    print(bracket_data)
    
    # Process scores into a dictionary for easier template access
    scores = {}
    
    # Process group stage match scores
    if bracket_data['group_stage']:
        for group_data in bracket_data['groups']:
            for match in group_data['matches']:
                match_scores = MatchScore.query.filter_by(match_id=match.id).order_by(MatchScore.set_number).all()
                scores[match.id] = match_scores

    has_group_stage = False

    if bracket_data['category'].format == TournamentFormat.GROUP_KNOCKOUT:
        has_group_stage = True
    else:
        has_group_stage = False

    # Process knockout stage match scores
    for round_num, matches in bracket_data['knockout_rounds'].items():
        for match in matches:
            match_scores = MatchScore.query.filter_by(match_id=match.id).order_by(MatchScore.set_number).all()
            scores[match.id] = match_scores
    
    return render_template('tournament/bracket.html',
                          title=f"{tournament.name} - {selected_category.category_type.value} Bracket",
                          tournament=tournament,
                          categories=categories,
                          selected_category=selected_category,
                          bracket_data=bracket_data,
                          scores=scores,
                          has_group_stage=has_group_stage,
                          format = bracket_data['category'].format)


@bp.route('/<int:id>/participants')
def participants(id):
    """Enhanced participants view with DUPR ratings info"""
    # Get tournament
    tournament = Tournament.query.get_or_404(id)
    
    # Get selected category (default to first category)
    categories = tournament.categories.all()
    if not categories:
        flash('No categories found for this tournament.', 'warning')
        return redirect(url_for('main.tournament_detail', id=id))
    
    category_id = request.args.get('category', type=int) or categories[0].id
    selected_category = TournamentCategory.query.get_or_404(category_id)
    
    # Get registrations for this category
    registrations = Registration.query.filter_by(category_id=category_id).all()
    
    # Get players from registrations with DUPR info
    participants = []
    for reg in registrations:
        if reg.is_approved:
            player = PlayerProfile.query.get(reg.player_id)
            partner = None
            if reg.partner_id:
                partner = PlayerProfile.query.get(reg.partner_id)
            
            # Get appropriate DUPR rating based on category
            player_dupr = None
            partner_dupr = None
            
            if selected_category.category_type == CategoryType.MENS_SINGLES:
                player_dupr = player.mens_singles_dupr if hasattr(player, 'mens_singles_dupr') else None
            elif selected_category.category_type == CategoryType.WOMENS_SINGLES:
                player_dupr = player.womens_singles_dupr if hasattr(player, 'womens_singles_dupr') else None
            elif selected_category.category_type == CategoryType.MENS_DOUBLES:
                player_dupr = player.mens_doubles_dupr if hasattr(player, 'mens_doubles_dupr') else None
                if partner:
                    partner_dupr = partner.mens_doubles_dupr if hasattr(partner, 'mens_doubles_dupr') else None
            elif selected_category.category_type == CategoryType.WOMENS_DOUBLES:
                player_dupr = player.womens_doubles_dupr if hasattr(player, 'womens_doubles_dupr') else None
                if partner:
                    partner_dupr = partner.womens_doubles_dupr if hasattr(partner, 'womens_doubles_dupr') else None
            elif selected_category.category_type == CategoryType.MIXED_DOUBLES:
                player_dupr = player.mixed_doubles_dupr if hasattr(player, 'mixed_doubles_dupr') else None
                if partner:
                    partner_dupr = partner.mixed_doubles_dupr if hasattr(partner, 'mixed_doubles_dupr') else None
            
            participants.append({
                'player': player,
                'partner': partner,
                'seed': reg.seed,
                'player_dupr': player_dupr,
                'partner_dupr': partner_dupr
            })
    
    # Sort by seed (if available)
    participants.sort(key=lambda x: x['seed'] if x['seed'] else 999)
    
    return render_template('tournament/participants.html',
                          title=f"{tournament.name} - {selected_category.category_type.value} Participants",
                          tournament=tournament,
                          categories=categories,
                          selected_category=selected_category,
                          participants=participants)

@bp.route('/<int:id>/prize_distribution')
def prize_distribution(id):
    """
    View for displaying prize money distribution across the tournament
    """
    # Get tournament
    tournament = Tournament.query.get_or_404(id)
    
    # Get all categories
    categories = tournament.categories.all()
    if not categories:
        flash('No categories found for this tournament.', 'warning')
        return redirect(url_for('main.tournament_detail', id=id))
    
    # Process prize information
    prize_info = {
        'total_prize_pool': tournament.prize_pool,
        'categories': []
    }
    
    for category in categories:
        category_prize = category.prize_money if hasattr(category, 'prize_money') else 0
        if category_prize == 0 and hasattr(category, 'prize_percentage'):
            # Calculate prize money if not already set
            category_prize = tournament.prize_pool * (category.prize_percentage / 100)
        
        # Get distribution
        distribution = {}
        if hasattr(category, 'prize_distribution') and category.prize_distribution:
            distribution = category.prize_distribution
        else:
            # Default distribution
            distribution = {
                "1": 50,
                "2": 25,
                "3-4": 12.5,
                "5-8": 6.25
            }
        
        # Calculate actual prize amounts
        prize_amounts = {}
        for place_range, percentage in distribution.items():
            prize_amounts[place_range] = category_prize * (percentage / 100)
        
        prize_info['categories'].append({
            'id': category.id,
            'name': category.category_type.value,
            'prize_money': category_prize,
            'percentage': category.prize_percentage if hasattr(category, 'prize_percentage') else 0,
            'distribution': distribution,
            'prize_amounts': prize_amounts
        })
    
    return render_template('tournament/prize_distribution.html',
                          title=f"{tournament.name} - Prize Distribution",
                          tournament=tournament,
                          prize_info=prize_info)

@bp.route('/api/<int:id>/bracket_data')
def api_bracket_data(id):
    """API endpoint to get bracket data for dynamic rendering"""
    # Get selected category
    category_id = request.args.get('category', type=int)
    if not category_id:
        return jsonify({'error': 'Category ID required'}), 400
    
    # Get bracket data using our service
    bracket_data = BracketService.get_bracket_data(category_id)
    
    # Format the response for JSON
    result = {
        'category': {
            'id': bracket_data['category'].id,
            'name': bracket_data['category'].category_type.value,
            'is_doubles': bracket_data['category'].is_doubles()
        },
        'format': str(bracket_data['format']),
        'group_stage': bracket_data['group_stage'],
        'groups': [],
        'knockout_rounds': {},
        'placings': []
    }
    
    # Process groups for JSON
    for group_data in bracket_data['groups']:
        group_info = {
            'id': group_data['group'].id,
            'name': group_data['group'].name,
            'standings': [],
            'matches': []
        }
        
        # Process standings
        for standing in group_data['standings']:
            if result['category']['is_doubles']:
                participant = standing.team
                name = f"{participant.player1.full_name}/{participant.player2.full_name}" if participant else "TBD"
            else:
                participant = standing.player
                name = participant.full_name if participant else "TBD"
            
            group_info['standings'].append({
                'id': standing.id,
                'participant_name': name,
                'matches_played': standing.matches_played,
                'matches_won': standing.matches_won,
                'matches_lost': standing.matches_lost,
                'sets_won': standing.sets_won,
                'sets_lost': standing.sets_lost,
                'position': standing.position
            })
        
        # Process matches
        for match in group_data['matches']:
            match_info = _format_match_for_api(match)
            group_info['matches'].append(match_info)
        
        result['groups'].append(group_info)
    
    # Process knockout rounds for JSON
    for round_num, matches in bracket_data['knockout_rounds'].items():
        result['knockout_rounds'][round_num] = []
        
        for match in matches:
            match_info = _format_match_for_api(match)
            result['knockout_rounds'][round_num].append(match_info)
    
    # Process placings if tournament is completed
    for placing in bracket_data['placings']:
        if 'participant' in placing and placing['participant']:
            participant = placing['participant']
            
            if placing.get('is_team', False):
                # Doubles team
                name = f"{participant.player1.full_name}/{participant.player2.full_name}" if participant else "TBD"
            else:
                # Singles player
                name = participant.full_name if participant else "TBD"
            
            result['placings'].append({
                'place': placing['place'],
                'participant_name': name,
                'points': placing.get('points', 0),
                'prize': placing.get('prize', 0)
            })
    
    return jsonify(result)
    
@bp.route('/api/<int:id>/placings')
def api_placings(id):
    """API endpoint to get placings data for a category"""
    # Get selected category
    category_id = request.args.get('category', type=int)
    if not category_id:
        return jsonify({'error': 'Category ID required'}), 400
    
    # Get category
    category = TournamentCategory.query.get_or_404(category_id)
    
    # Get placings using our service
    placings = PlacingService.get_placings(category_id)
    
    # Format for API response
    result = {
        'category': {
            'id': category.id,
            'name': category.category_type.value,
            'points_awarded': category.points_awarded,
            'prize_money': category.prize_money if hasattr(category, 'prize_money') else 0
        },
        'placings': []
    }
    
    # Format placings
    for placing in placings:
        participant = placing.get('participant')
        is_team = placing.get('is_team', False)
        
        placing_info = {
            'place': placing['place'],
            'points': placing.get('points', 0),
            'prize': float(placing.get('prize', 0))
        }
        
        if participant:
            if is_team:
                placing_info['participant'] = {
                    'team_id': participant.id,
                    'player1': {
                        'id': participant.player1.id,
                        'name': participant.player1.full_name
                    },
                    'player2': {
                        'id': participant.player2.id,
                        'name': participant.player2.full_name
                    }
                }
            else:
                placing_info['participant'] = {
                    'id': participant.id,
                    'name': participant.full_name
                }
        
        result['placings'].append(placing_info)
    
    return jsonify(result)
    
@bp.route('/<int:id>/schedule')
def schedule(id):
    # Get tournament
    tournament = Tournament.query.get_or_404(id)
    
    # Get categories to allow filtering
    categories = tournament.categories.all()
    
    # Get filter parameters
    category_id = request.args.get('category', type=int)
    search_query = request.args.get('search', '')
    stage_filter = request.args.get('stage', '')
    
    # Base query
    if category_id:
        matches_query = Match.query.join(TournamentCategory).filter(
            TournamentCategory.tournament_id == id,
            TournamentCategory.id == category_id,
            Match.scheduled_time.isnot(None)
        )
    else:
        matches_query = Match.query.join(TournamentCategory).filter(
            TournamentCategory.tournament_id == id,
            Match.scheduled_time.isnot(None)
        )
    
    # Execute the query to get all matches (we'll organize and filter in Python)
    all_matches = matches_query.all()
    
    # Extract available stages for filter options
    available_stages = {
        'knockout': set(),  # Set of round numbers
        'groups': set()     # Set of group names
    }
    
    for match in all_matches:
        if match.stage.name == 'GROUP' and match.group:
            available_stages['groups'].add(match.group.name)
        elif match.stage.name == 'KNOCKOUT':
            available_stages['knockout'].add(match.round)
    
    # Sort the sets for consistent display
    available_stages['groups'] = sorted(available_stages['groups'])
    available_stages['knockout'] = reversed(sorted(available_stages['knockout']))
    
    # Filter matches by player name if search is provided
    if search_query:
        filtered_matches = []
        search_query = search_query.lower()
        
        for match in all_matches:
            # Check player names for singles matches
            if match.player1 and match.player1.full_name.lower().find(search_query) != -1:
                filtered_matches.append(match)
                continue
            if match.player2 and match.player2.full_name.lower().find(search_query) != -1:
                filtered_matches.append(match)
                continue
                
            # Check player names for doubles matches
            if match.is_doubles:
                if match.team1:
                    if (match.team1.player1 and match.team1.player1.full_name.lower().find(search_query) != -1) or \
                       (match.team1.player2 and match.team1.player2.full_name.lower().find(search_query) != -1):
                        filtered_matches.append(match)
                        continue
                
                if match.team2:
                    if (match.team2.player1 and match.team2.player1.full_name.lower().find(search_query) != -1) or \
                       (match.team2.player2 and match.team2.player2.full_name.lower().find(search_query) != -1):
                        filtered_matches.append(match)
                        continue
        
        all_matches = filtered_matches
    
    # Filter by stage if specified
    if stage_filter:
        if stage_filter.startswith('group:'):
            # Filter by specific group
            group_name = stage_filter[6:]  # Remove 'group:' prefix
            all_matches = [m for m in all_matches if m.stage.name == 'GROUP' and m.group and m.group.name == group_name]
        elif stage_filter.isdigit():
            # For knockout rounds (e.g., "1" for finals, "2" for semis)
            round_num = int(stage_filter)
            all_matches = [m for m in all_matches if m.stage.name == 'KNOCKOUT' and m.round == round_num]
    
    # Organize matches by stage and round
    stages = {}
    
    # Process group stage matches
    group_matches = [m for m in all_matches if m.stage.name == 'GROUP']
    if group_matches:
        # Group by the group name
        groups = {}
        for match in group_matches:
            group_name = match.group.name if match.group else "Unknown Group"
            if group_name not in groups:
                groups[group_name] = []
            groups[group_name].append(match)
        
        # Sort groups alphabetically
        sorted_groups = dict(sorted(groups.items()))
        stages['group'] = sorted_groups
    
    # Process knockout matches
    knockout_matches = [m for m in all_matches if m.stage.name == 'KNOCKOUT']
    if knockout_matches:
        rounds = {}
        for match in knockout_matches:
            round_num = match.round
            round_name = match.round_name
            if round_num not in rounds:
                rounds[round_num] = {
                    'name': round_name,
                    'matches': []
                }
            rounds[round_num]['matches'].append(match)
        
        # Sort rounds
        sorted_rounds = dict(reversed(sorted(rounds.items())))
        stages['knockout'] = sorted_rounds
    
    # Get selected category if filtering
    selected_category = None
    if category_id:
        selected_category = TournamentCategory.query.get(category_id)
    
    return render_template('tournament/schedule.html',
                          title=f"{tournament.name} - Schedule",
                          tournament=tournament,
                          stages=stages,
                          categories=categories,
                          selected_category=selected_category,
                          search_query=search_query,
                          stage_filter=stage_filter,
                          available_stages=available_stages)

@bp.route('/<int:id>/live_scoring')
def live_scoring(id):
    # Get tournament
    tournament = Tournament.query.get_or_404(id)
    
    # Check if tournament is ongoing
    if tournament.status != TournamentStatus.ONGOING:
        flash('Live scoring is only available for ongoing tournaments.', 'warning')
        return redirect(url_for('main.tournament_detail', id=id))
    
    # Get all ongoing matches (both singles and doubles)
    ongoing_matches = Match.query.join(TournamentCategory).filter(
        TournamentCategory.tournament_id == id,
        Match.completed == False,
        # For singles matches OR doubles matches
        ((Match.player1_id.isnot(None) & Match.player2_id.isnot(None)) |
         (Match.team1_id.isnot(None) & Match.team2_id.isnot(None)))
    ).all()
    
    # Get match scores
    scores = {}
    for match in ongoing_matches:
        match_scores = MatchScore.query.filter_by(match_id=match.id).order_by(MatchScore.set_number).all()
        scores[match.id] = match_scores
    
    return render_template('tournament/live_scoring.html',
                           title=f"{tournament.name} - Live Scoring",
                           tournament=tournament,
                           ongoing_matches=ongoing_matches,
                           scores=scores)

@bp.route('/<int:id>/results')
def results(id):
    """
    Enhanced results view with complete tournament placings, 
    prize money, and points information
    """
    # Get tournament
    tournament = Tournament.query.get_or_404(id)
    
    # Check if tournament is completed
    if tournament.status != TournamentStatus.COMPLETED:
        flash('Results are only available for completed tournaments.', 'warning')
        return redirect(url_for('main.tournament_detail', id=id))
    
    # Get selected category (default to first category)
    categories = tournament.categories.all()
    if not categories:
        flash('No categories found for this tournament.', 'warning')
        return redirect(url_for('main.tournament_detail', id=id))
    
    category_id = request.args.get('category', type=int) or categories[0].id
    selected_category = TournamentCategory.query.get_or_404(category_id)
    
    # Get tournament placings using PlacingService
    placings = PlacingService.get_placings(category_id)
    
    # Extract winners for the podium (1st, 2nd, 3rd)
    winners = {
        'first': next((p['participant'] for p in placings if p['place'] == 1), None),
        'second': next((p['participant'] for p in placings if p['place'] == 2), None),
        'third': next((p['participant'] for p in placings if p['place'] == 3), None),
        'fourth': next((p['participant'] for p in placings if p['place'] == 4), None)
    }
    
    # Get all completed matches for this category
    matches = Match.query.filter_by(
        category_id=category_id,
        completed=True
    ).order_by(Match.round).all()
    
    # Get prize distribution information
    prize_info = {
        'total_prize_pool': tournament.prize_pool,
        'category_prize': selected_category.prize_money if hasattr(selected_category, 'prize_money') else 0,
        'category_percentage': selected_category.prize_percentage if hasattr(selected_category, 'prize_percentage') else 0,
        'distribution': {}
    }
    
    # Format prize distribution for display
    if hasattr(selected_category, 'prize_distribution') and selected_category.prize_distribution:
        prize_info['distribution'] = selected_category.prize_distribution
    else:
        # Default distribution
        prize_info['distribution'] = {
            "1": 50,
            "2": 25,
            "3-4": 12.5,
            "5-8": 6.25
        }
    
    # Format points distribution for display
    points_info = {
        'total_category_points': selected_category.points_awarded,
        'distribution': {}
    }
    
    if hasattr(selected_category, 'points_distribution') and selected_category.points_distribution:
        points_info['distribution'] = selected_category.points_distribution
    else:
        # Default distribution
        points_info['distribution'] = {
            "1": 100,
            "2": 70, 
            "3-4": 50,
            "5-8": 25,
            "9-16": 15
        }
    
    # Group placings for display
    grouped_placings = {}
    for placing in placings:
        place = placing['place']
        if place not in grouped_placings:
            grouped_placings[place] = []
        grouped_placings[place].append(placing)
    
    return render_template('tournament/results.html',
                          title=f"{tournament.name} - Results",
                          tournament=tournament,
                          categories=categories,
                          selected_category=selected_category,
                          winners=winners,
                          placings=placings,
                          grouped_placings=grouped_placings,
                          matches=matches,
                          prize_info=prize_info,
                          points_info=points_info)


@bp.route('/<int:id>/match/<int:match_id>')
def match_detail(id, match_id):
    # Get tournament and match
    tournament = Tournament.query.get_or_404(id)
    match = Match.query.get_or_404(match_id)
    
    # Verify match belongs to this tournament
    if match.category.tournament_id != id:
        flash('Match not found in this tournament.', 'danger')
        return redirect(url_for('main.tournament_detail', id=id))
    
    # Get match scores
    scores = MatchScore.query.filter_by(match_id=match_id).order_by(MatchScore.set_number).all()
    
    return render_template('tournament/match_detail.html',
                           title=f"{tournament.name} - Match Details",
                           now=datetime.now(),
                           tournament=tournament,
                           match=match,
                           scores=scores)

# Route removed as match_detail.html now handles live scoring functionality

@bp.route('/<int:id>/live_courts')
def live_courts(id):
    """
    Live view of all courts in a tournament, showing active matches and next scheduled matches
    """
    # Get tournament
    tournament = Tournament.query.get_or_404(id)
    
    # Check if tournament is ongoing
    if tournament.status != TournamentStatus.ONGOING:
        flash('Live court view is only available for ongoing tournaments.', 'warning')
        return redirect(url_for('main.tournament_detail', id=id))
    
    # Get all matches with court assignments for this tournament
    all_assigned_matches = Match.query.join(TournamentCategory).filter(
        TournamentCategory.tournament_id == id,
        Match.court.isnot(None)
    ).order_by(Match.scheduled_time).all()
    
    # Organize matches by court
    courts = {}
    # Get ongoing matches (not completed, have players/teams assigned, and have a court)
    ongoing_matches = {}
    # Get upcoming matches by court (next scheduled match for each court)
    upcoming_matches = {}
    
    # Current time for comparison
    now = datetime.now()
    
    # Process all assigned matches to organize them by court
    for match in all_assigned_matches:
        court = match.court
        
        # Add court to dictionaries if not already present
        if court not in courts:
            courts[court] = []
        if court not in ongoing_matches:
            ongoing_matches[court] = None
        if court not in upcoming_matches:
            upcoming_matches[court] = None
        
        # Add match to the court's matches list
        courts[court].append(match)
        
        # Check if this is an ongoing match
        if not match.completed and (
            (match.is_doubles and match.team1_id and match.team2_id) or
            (not match.is_doubles and match.player1_id and match.player2_id)
        ):
            # If no ongoing match for this court or this match is more recent, use this one
            if ongoing_matches[court] is None:
                ongoing_matches[court] = match
            elif match.scheduled_time and ongoing_matches[court].scheduled_time:
                # If match is more recent (closer to now) than the current ongoing match
                if abs((match.scheduled_time - now).total_seconds()) < abs((ongoing_matches[court].scheduled_time - now).total_seconds()):
                    ongoing_matches[court] = match
        
        # Check if this is an upcoming match
        if not match.completed and match.scheduled_time and match.scheduled_time > now:
            # If no upcoming match for this court yet or this one is scheduled sooner
            if upcoming_matches[court] is None:
                upcoming_matches[court] = match
            elif match.scheduled_time and upcoming_matches[court].scheduled_time:
                # Use the match that's scheduled earlier as the next match
                if match.scheduled_time < upcoming_matches[court].scheduled_time:
                    upcoming_matches[court] = match
    
    # Get match scores for ongoing matches
    scores = {}
    for court, match in ongoing_matches.items():
        if match:
            match_scores = MatchScore.query.filter_by(match_id=match.id).order_by(MatchScore.set_number).all()
            scores[match.id] = match_scores
    
    return render_template('tournament/live_courts.html',
                           title=f"{tournament.name} - Live Courts",
                           tournament=tournament,
                           courts=courts,
                           ongoing_matches=ongoing_matches,
                           upcoming_matches=upcoming_matches,
                           scores=scores,
                           now=now)

# Add this API endpoint after the api_scores function
@bp.route('/api/<int:id>/courts_data')
def api_courts_data(id):
    """API endpoint for live court status data"""
    # Get tournament
    tournament = Tournament.query.get_or_404(id)
    
    # Get all matches with court assignments for this tournament
    all_assigned_matches = Match.query.join(TournamentCategory).filter(
        TournamentCategory.tournament_id == id,
        Match.court.isnot(None)
    ).order_by(Match.scheduled_time).all()
    
    # Organize matches by court
    courts_data = {}
    now = datetime.now()
    
    for match in all_assigned_matches:
        court = match.court
        
        # Initialize court data if not exists
        if court not in courts_data:
            courts_data[court] = {
                'ongoing_match': None,
                'upcoming_match': None
            }
        
        # Check if match is ongoing (not completed and has players/teams assigned)
        if not match.completed and (
            (match.is_doubles and match.team1_id and match.team2_id) or
            (not match.is_doubles and match.player1_id and match.player2_id)
        ):
            current_ongoing = courts_data[court]['ongoing_match']
            
            # If no ongoing match yet or this match is scheduled earlier
            if current_ongoing is None or (
                match.scheduled_time and current_ongoing.get('scheduled_time') and
                match.scheduled_time < datetime.fromisoformat(current_ongoing['scheduled_time'])
            ):
                # Format match data for JSON
                courts_data[court]['ongoing_match'] = _format_match_for_api(match)
        
        # Check if match is upcoming
        if not match.completed and match.scheduled_time and match.scheduled_time > now:
            current_upcoming = courts_data[court]['upcoming_match']
            
            # If no upcoming match yet or this match is scheduled earlier
            if current_upcoming is None or (
                match.scheduled_time and current_upcoming.get('scheduled_time') and
                match.scheduled_time < datetime.fromisoformat(current_upcoming['scheduled_time'])
            ):
                # Format match data for JSON
                courts_data[court]['upcoming_match'] = _format_match_for_api(match)
    
    return jsonify(courts_data)
    
@bp.route('/api/<int:id>/scores')
def api_scores(id):
    # API endpoint to get latest scores for all matches in a tournament
    # This can be used for live updates via AJAX
    
    # Get all ongoing matches for this tournament (both singles and doubles)
    ongoing_matches = Match.query.join(TournamentCategory).filter(
        TournamentCategory.tournament_id == id,
        Match.completed == False,
        # For singles matches OR doubles matches
        ((Match.player1_id.isnot(None) & Match.player2_id.isnot(None)) |
         (Match.team1_id.isnot(None) & Match.team2_id.isnot(None)))
    ).all()
    
    result = []
    for match in ongoing_matches:
        scores = MatchScore.query.filter_by(match_id=match.id).order_by(MatchScore.set_number).all()
        
        # Handle both singles and doubles matches appropriately
        if match.is_doubles:
            match_data = {
                'match_id': match.id,
                'is_doubles': True,
                'scores': [
                    {
                        'set': score.set_number,
                        'player1_score': score.player1_score,
                        'player2_score': score.player2_score
                    } for score in scores
                ]
            }
            
            # Add team information
            if match.team1:
                match_data['team1'] = {
                    'player1': match.team1.player1.full_name,
                    'player2': match.team1.player2.full_name
                }
            else:
                match_data['team1'] = {'player1': 'TBD', 'player2': 'TBD'}
                
            if match.team2:
                match_data['team2'] = {
                    'player1': match.team2.player1.full_name,
                    'player2': match.team2.player2.full_name
                }
            else:
                match_data['team2'] = {'player1': 'TBD', 'player2': 'TBD'}
        else:
            # Singles match
            match_data = {
                'match_id': match.id,
                'is_doubles': False,
                'player1': match.player1.full_name if match.player1 else 'TBD',
                'player2': match.player2.full_name if match.player2 else 'TBD',
                'scores': [
                    {
                        'set': score.set_number,
                        'player1_score': score.player1_score,
                        'player2_score': score.player2_score
                    } for score in scores
                ]
            }
        
        result.append(match_data)
    
    return jsonify(result)
