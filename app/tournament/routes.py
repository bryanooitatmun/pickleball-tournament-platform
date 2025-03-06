from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user, login_required
from app import db
from app.tournament import bp
from app.models import Tournament, TournamentCategory, Match, MatchScore, Registration, PlayerProfile, TournamentStatus, CategoryType, Team
from datetime import datetime

@bp.route('/<int:id>/bracket')
def bracket(id):
    # Get tournament
    tournament = Tournament.query.get_or_404(id)
    
    # Get selected category (default to first category)
    categories = tournament.categories.all()
    if not categories:
        flash('No categories found for this tournament.', 'warning')
        return redirect(url_for('main.tournament_detail', id=id))
    
    category_id = request.args.get('category', type=int) or categories[0].id
    selected_category = TournamentCategory.query.get_or_404(category_id)
    
    # Get matches for this category, ordered by round and match_order
    matches = Match.query.filter_by(category_id=category_id).order_by(Match.round.desc(), Match.match_order).all()

    # Get match scores
    scores = {}
    for match in matches:
        match_scores = MatchScore.query.filter_by(match_id=match.id).order_by(MatchScore.set_number).all()
        scores[match.id] = match_scores
    
    return render_template('tournament/bracket.html',
                           title=f"{tournament.name} - {selected_category.category_type.value} Bracket",
                           tournament=tournament,
                           categories=categories,
                           selected_category=selected_category,
                           matches=matches,
                           scores=scores)

@bp.route('/<int:id>/participants')
def participants(id):
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
    
    # Get players from registrations
    participants = []
    for reg in registrations:
        player = PlayerProfile.query.get(reg.player_id)
        partner = None
        if reg.partner_id:
            partner = PlayerProfile.query.get(reg.partner_id)
        
        participants.append({
            'player': player,
            'partner': partner,
            'seed': reg.seed
        })
    
    # Sort by seed (if available)
    participants.sort(key=lambda x: x['seed'] if x['seed'] else 999)
    
    return render_template('tournament/participants.html',
                           title=f"{tournament.name} - {selected_category.category_type.value} Participants",
                           tournament=tournament,
                           categories=categories,
                           selected_category=selected_category,
                           participants=participants)

@bp.route('/<int:id>/schedule')
def schedule(id):
    # Get tournament
    tournament = Tournament.query.get_or_404(id)
    
    # Get all matches with court and time info
    matches = Match.query.join(TournamentCategory).filter(
        TournamentCategory.tournament_id == id,
        Match.court.isnot(None),
        Match.scheduled_time.isnot(None)
    ).order_by(Match.scheduled_time).all()
    
    # Group matches by day
    days = {}
    for match in matches:
        day = match.scheduled_time.date()
        if day not in days:
            days[day] = []
        days[day].append(match)
    
    return render_template('tournament/schedule.html',
                           title=f"{tournament.name} - Schedule",
                           tournament=tournament,
                           days=days)

@bp.route('/<int:id>/live_scoring')
def live_scoring(id):
    # Get tournament
    tournament = Tournament.query.get_or_404(id)
    
    # Check if tournament is ongoing
    if tournament.status != TournamentStatus.ONGOING:
        flash('Live scoring is only available for ongoing tournaments.', 'warning')
        return redirect(url_for('main.tournament_detail', id=id))
    
    # Get all ongoing matches
    ongoing_matches = Match.query.join(TournamentCategory).filter(
        TournamentCategory.tournament_id == id,
        Match.completed == False,
        Match.player1_id.isnot(None),
        Match.player2_id.isnot(None)
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
    
    # Get matches for this category that have winners
    matches = Match.query.filter_by(
        category_id=category_id,
        completed=True
    ).order_by(Match.round).all()
    
    # Get winners (1st, 2nd, 3rd place)
    winners = {
        'first': None,
        'second': None,
        'third': None,
        'fourth': None
    }
    
    # Determine if this is a doubles category
    is_doubles = selected_category.category_type in [
        CategoryType.MENS_DOUBLES, 
        CategoryType.WOMENS_DOUBLES, 
        CategoryType.MIXED_DOUBLES
    ]
    
    for match in matches:
        if match.round == 1:  # Final
            if is_doubles:
                # Doubles match
                if match.winning_team_id:
                    winning_team = Team.query.get(match.winning_team_id)
                    if winning_team:
                        winners['first'] = [
                            PlayerProfile.query.get(winning_team.player1_id),
                            PlayerProfile.query.get(winning_team.player2_id)
                        ]
                
                if match.losing_team_id:
                    losing_team = Team.query.get(match.losing_team_id)
                    if losing_team:
                        winners['second'] = [
                            PlayerProfile.query.get(losing_team.player1_id),
                            PlayerProfile.query.get(losing_team.player2_id)
                        ]
            else:
                # Singles match
                if match.winning_player_id:
                    winners['first'] = match.winning_player
                
                if match.losing_player_id:
                    winners['second'] = match.losing_player
        
        elif match.round == 2:  # Semifinals
            # Process semifinal losers for 3rd/4th place
            # Similar logic as above, but for semifinal matches
            # You'll need to adapt this for singles vs doubles
            pass
    
    return render_template('tournament/results.html',
                           title=f"{tournament.name} - Results",
                           tournament=tournament,
                           categories=categories,
                           selected_category=selected_category,
                           winners=winners,
                           matches=matches)

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

@bp.route('/<int:id>/match/<int:match_id>/live')
def live_match(id, match_id):
    # Get tournament and match
    tournament = Tournament.query.get_or_404(id)
    match = Match.query.get_or_404(match_id)
    
    # Verify match belongs to this tournament
    if match.category.tournament_id != id:
        flash('Match not found in this tournament.', 'danger')
        return redirect(url_for('main.tournament_detail', id=id))
    
    # Check if match is ongoing
    if match.completed:
        flash('This match has already been completed.', 'warning')
        return redirect(url_for('tournament.match_detail', id=id, match_id=match_id))
    
    # Get match scores
    scores = MatchScore.query.filter_by(match_id=match_id).order_by(MatchScore.set_number).all()
    
    return render_template('tournament/live_match.html',
                           title=f"{tournament.name} - Live Match",
                           tournament=tournament,
                           match=match,
                           scores=scores)

@bp.route('/api/<int:id>/scores')
def api_scores(id):
    # API endpoint to get latest scores for all matches in a tournament
    # This can be used for live updates via AJAX
    
    # Get all ongoing matches for this tournament
    ongoing_matches = Match.query.join(TournamentCategory).filter(
        TournamentCategory.tournament_id == id,
        Match.completed == False,
        Match.player1_id.isnot(None),
        Match.player2_id.isnot(None)
    ).all()
    
    result = []
    for match in ongoing_matches:
        scores = MatchScore.query.filter_by(match_id=match.id).order_by(MatchScore.set_number).all()
        match_data = {
            'match_id': match.id,
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
        
        # Add doubles partner info if applicable
        if match.player1_partner:
            match_data['player1_partner'] = match.player1_partner.full_name
        if match.player2_partner:
            match_data['player2_partner'] = match.player2_partner.full_name
        
        result.append(match_data)
    
    return jsonify(result)
