from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import current_user, login_required
from app import db
from app.main import bp
from app.models import Tournament, TournamentCategory, PlayerProfile, Match, CategoryType, TournamentStatus, PlatformSponsor, Venue, Advertisement
from app.services import BracketService, PlacingService, PrizeService, RegistrationService
from datetime import datetime
import os

# @bp.route('/')
# @bp.route('/index')
# def index():
#     # Featured tournament (current or upcoming)
#     featured_tournament = Tournament.query.filter_by(is_featured=True).first()
#     if not featured_tournament:
#         # If no featured tournament, get the nearest upcoming one
#         featured_tournament = Tournament.query.filter_by(status=TournamentStatus.UPCOMING).order_by(Tournament.start_date).first()
    
#     # Get upcoming tournaments
#     upcoming_tournaments = Tournament.query.filter_by(status=TournamentStatus.UPCOMING).order_by(Tournament.start_date).limit(3).all()
    
#     # Get top players for each category
#     top_mens_singles = PlayerProfile.query.order_by(PlayerProfile.mens_singles_points.desc()).limit(5).all()
#     top_womens_singles = PlayerProfile.query.order_by(PlayerProfile.womens_singles_points.desc()).limit(5).all()
#     top_mens_doubles = PlayerProfile.query.order_by(PlayerProfile.mens_doubles_points.desc()).limit(5).all()
#     top_womens_doubles = PlayerProfile.query.order_by(PlayerProfile.womens_doubles_points.desc()).limit(5).all()
#     top_mixed_doubles = PlayerProfile.query.order_by(PlayerProfile.mixed_doubles_points.desc()).limit(5).all()
    
#     # Get featured sponsors
#     featured_platform_sponsors = PlatformSponsor.query.filter_by(is_featured=True).all()
    
#     # Get featured venues
#     featured_venues = Venue.query.filter_by(is_featured=True).limit(3).all()
    
#     # Get active advertisements
#     hero_ads = Advertisement.query.filter_by(
#         position='hero', 
#         is_active=True
#     ).filter(
#         Advertisement.start_date <= datetime.utcnow(),
#         Advertisement.end_date >= datetime.utcnow()
#     ).all()
    
#     sidebar_ads = Advertisement.query.filter_by(
#         position='sidebar', 
#         is_active=True
#     ).filter(
#         Advertisement.start_date <= datetime.utcnow(),
#         Advertisement.end_date >= datetime.utcnow()
#     ).all()
    
#     return render_template('main/index.html', 
#                           title='Home',
#                           featured_tournament=featured_tournament,
#                           upcoming_tournaments=upcoming_tournaments,
#                           top_mens_singles=top_mens_singles,
#                           top_womens_singles=top_womens_singles,
#                           top_mens_doubles=top_mens_doubles,
#                           top_womens_doubles=top_womens_doubles,
#                           top_mixed_doubles=top_mixed_doubles,
#                           featured_platform_sponsors=featured_platform_sponsors,
#                           featured_venues=featured_venues,
#                           hero_ads=hero_ads,
#                           sidebar_ads=sidebar_ads,
#                           now=datetime.now())

@bp.route('/')
@bp.route('/index')
def index():
    id = 1
    tournament = Tournament.query.get_or_404(id)
    categories = tournament.categories.order_by(TournamentCategory.display_order).all()
    
    # For ongoing or completed tournaments, get matches
    matches = {}
    winners = {}
    
    if tournament.status in [TournamentStatus.ONGOING, TournamentStatus.COMPLETED]:
        for category in categories:
            # Fixed query: Use Match model directly instead of relationship
            matches[category.id] = Match.query.filter_by(category_id=category.id).order_by(Match.round.desc(), Match.match_order).all()
            
            # For completed tournaments, get winners
            if tournament.status == TournamentStatus.COMPLETED:
                # Get final match for each category - Fixed query
                final_match = Match.query.filter_by(category_id=category.id, round=1).first()
                if final_match and hasattr(final_match, 'winner_id') and final_match.winner_id:
                    winners[category.id] = final_match.winner
    
    return render_template('main/tournament_detail.html',
                           title=tournament.name,
                           tournament=tournament,
                           categories=categories,
                           matches=matches,
                           winners=winners)


@bp.route('/sponsors')
def sponsors():
    sponsors = PlatformSponsor.query.all()
    return render_template('main/platform_sponsors.html', title='Our Sponsors', sponsors=sponsors)


@bp.route('/events')
def events():
    # Get upcoming and past tournaments
    upcoming_tournaments = Tournament.query.filter(Tournament.status != TournamentStatus.COMPLETED).order_by(Tournament.start_date).all()
    past_tournaments = Tournament.query.filter_by(status=TournamentStatus.COMPLETED).order_by(Tournament.end_date.desc()).all()
    
    # Group events by month
    upcoming_by_month = {}
    for tournament in upcoming_tournaments:
        month = tournament.start_date.strftime('%B').upper()
        if month not in upcoming_by_month:
            upcoming_by_month[month] = []
        upcoming_by_month[month].append(tournament)
    
    past_by_month = {}
    for tournament in past_tournaments:
        month = tournament.end_date.strftime('%B').upper()
        if month not in past_by_month:
            past_by_month[month] = []
        past_by_month[month].append(tournament)

    # Get tournament tiers for the legend
    tiers = current_app.config['TOURNAMENT_TIERS']
    
    return render_template('main/events.html', 
                           title='Events',
                           upcoming_by_month=upcoming_by_month,
                           past_by_month=past_by_month,
                           tiers=tiers)

@bp.route('/tournament/<int:id>')
def tournament_detail(id):
    tournament = Tournament.query.get_or_404(id)
    categories = tournament.categories.all()
    
    # For ongoing or completed tournaments, get matches
    matches = {}
    winners = {}
    
    if tournament.status in [TournamentStatus.ONGOING, TournamentStatus.COMPLETED]:
        for category in categories:
            # Fixed query: Use Match model directly instead of relationship
            matches[category.id] = Match.query.filter_by(category_id=category.id).order_by(Match.round.desc(), Match.match_order).all()
            
            # For completed tournaments, get winners
            if tournament.status == TournamentStatus.COMPLETED:
                # Get final match for each category - Fixed query
                final_match = Match.query.filter_by(category_id=category.id, round=1).first()
                if final_match and hasattr(final_match, 'winner_id') and final_match.winner_id:
                    winners[category.id] = final_match.winner
    
    return render_template('main/tournament_detail.html',
                           title=tournament.name,
                           tournament=tournament,
                           categories=categories,
                           matches=matches,
                           winners=winners)

@bp.route('/player/<int:id>')
def player_detail(id):
    player = PlayerProfile.query.get_or_404(id)
    
    # Get recent tournaments for this player
    recent_tournaments = []
    registrations = player.registrations.all()
    for registration in registrations:
        tournament = registration.category.tournament
        if tournament not in recent_tournaments:
            recent_tournaments.append(tournament)
    
    # Sort tournaments by date (newest first)
    recent_tournaments.sort(key=lambda x: x.start_date, reverse=True)
    
    # Get equipment and sponsors
    equipment = player.equipment.all()
    sponsors = player.player_sponsors.all()
    
    return render_template('main/player_detail.html',
                           title=player.full_name,
                           player=player,
                           recent_tournaments=recent_tournaments[:5],
                           equipment=equipment,
                           sponsors=sponsors)

@bp.route('/rankings')
def rankings():
    category = request.args.get('category', 'mens_singles')
    
    if category == 'mens_singles':
        players = PlayerProfile.query.filter(PlayerProfile.mens_singles_points > 0).order_by(PlayerProfile.mens_singles_points.desc()).all()
        title = "Men's Singles Rankings"
    elif category == 'womens_singles':
        players = PlayerProfile.query.filter(PlayerProfile.womens_singles_points > 0).order_by(PlayerProfile.womens_singles_points.desc()).all()
        title = "Women's Singles Rankings"
    elif category == 'mens_doubles':
        players = PlayerProfile.query.filter(PlayerProfile.mens_doubles_points > 0).order_by(PlayerProfile.mens_doubles_points.desc()).all()
        title = "Men's Doubles Rankings"
    elif category == 'womens_doubles':
        players = PlayerProfile.query.filter(PlayerProfile.womens_doubles_points > 0).order_by(PlayerProfile.womens_doubles_points.desc()).all()
        title = "Women's Doubles Rankings"
    elif category == 'mixed_doubles':
        players = PlayerProfile.query.filter(PlayerProfile.mixed_doubles_points > 0).order_by(PlayerProfile.mixed_doubles_points.desc()).all()
        title = "Mixed Doubles Rankings"
    else:
        # Default to men's singles
        players = PlayerProfile.query.filter(PlayerProfile.mens_singles_points > 0).order_by(PlayerProfile.mens_singles_points.desc()).all()
        title = "Men's Singles Rankings"
    
    # Add rank to each player
    for i, player in enumerate(players):
        player.rank = i + 1
    
    return render_template('main/rankings.html',
                           title=title,
                           players=players,
                           current_category=category,
                           categories=current_app.config['TOURNAMENT_CATEGORIES'])
