"""
Enhanced seed script populated with real PPA Tour data from website
"""
import os
import sys
from datetime import datetime, timedelta
import random
from flask import Flask
from app import create_app, db
from app.models import (
    User, UserRole, Tournament, TournamentCategory, 
    TournamentTier, TournamentFormat, TournamentStatus, 
    CategoryType, PlayerProfile, Registration, Match,
    MatchScore, Team, Group, GroupStanding, MatchStage,
    Equipment, PlayerSponsor, PlatformSponsor
)

# Import services if they exist
try:
    from app.services import BracketService, PlacingService, PrizeService
    SERVICES_AVAILABLE = True
    print("Using service layer for tournament management")
except ImportError:
    SERVICES_AVAILABLE = False
    print("Service layer not found, using direct database operations")

# Create app context
app = create_app()
app.app_context().push()

# Data extracted from PPA website
PPA_PLAYERS = [
    {"rank": 1, "name": "Federico Staksrud", "country": "Argentina", "age": 29, "points": 15900, "plays": "Right-handed", "profile_image": "https://images.pickleball.com/profile-images/1739907562636/ed6de488-e07a-4eb6-b8b1-abbdc407a162.png"},
    {"rank": 2, "name": "Ben Johns", "country": "United States", "age": 25, "points": 15800, "plays": "Right-handed", "profile_image": "https://images.pickleball.com/profile-images/1720555369461/lmbA0oL0.jpeg"},
    {"rank": 3, "name": "Collin Johns", "country": "United States", "age": 31, "points": 14100, "plays": "Right-handed", "profile_image": "https://images.pickleball.com/profile-images/1720556310963/sh5fPiWw.jpeg"},
    {"rank": 4, "name": "JW Johnson", "country": "United States", "age": 22, "points": 13800, "plays": "Right-handed", "profile_image": "https://images.pickleball.com/profile-images/1720559477443/8kPIUGoM.jpeg"},
    {"rank": 5, "name": "Andrei Daescu", "country": "Romania", "age": 37, "points": 13300, "plays": "Right-handed", "profile_image": "https://images.pickleball.com/profile-images/1720542964791/z3CAJNTQ.jpeg"},
    {"rank": 6, "name": "Hayden Patriquin", "country": "United States", "age": 19, "points": 13000, "plays": "Right-handed", "profile_image": "https://images.pickleball.com/profile-images/1720559022236/v6UY7T_M.jpeg"},
    {"rank": 7, "name": "Dylan Frazier", "country": "United States", "age": 23, "points": 12900, "plays": "Right-handed", "profile_image": "https://images.pickleball.com/profile-images/1699576909927/Dylan-No-Smile.png"},
    {"rank": 8, "name": "Christian Alshon", "country": "United States", "age": 24, "points": 11350, "plays": "Right-handed", "profile_image": "https://images.pickleball.com/profile-images/1720556173362/KVxYCblA.jpeg"},
    {"rank": 9, "name": "Gabriel Tardio", "country": "Bolivia", "age": 19, "points": 11300, "plays": "Right-handed", "profile_image": "https://images.pickleball.com/profile-images/1738097943956/PPA_MEDIADAY_GABE_TARDIO-3-removebg-preview.png"},
    {"rank": 10, "name": "Dekel Bar", "country": "Israel", "age": 31, "points": 11200, "plays": "Right-handed", "profile_image": "https://images.pickleball.com/profile-images/1739205003646/PPA_MEDIADAY_DEKELBAR-4.jpg"},
    {"rank": 11, "name": "Pablo Tellez", "country": "Colombia", "age": 29, "points": 10200, "plays": "Right-handed", "profile_image": "https://images.pickleball.com/profile-images/1720628535561/EioiuDRA.jpeg"},
    {"rank": 12, "name": "Tyson McGuffin", "country": "United States", "age": 35, "points": 10100, "plays": "Right-handed", "profile_image": "https://images.pickleball.com/profile-images/1720632190280/__xxtk2s.jpeg"},
    {"rank": 13, "name": "Matt Wright", "country": "United States", "age": 47, "points": 8600, "plays": "Right-handed", "profile_image": "https://images.pickleball.com/profile-images/1700084603525/matt-headshot-e1654201906527-removebg-preview.png"},
    {"rank": 14, "name": "Jaume Martinez Vich", "country": "Spain", "age": 31, "points": 7250, "plays": "Right-handed", "profile_image": "https://images.pickleball.com/profile-images/1720559550831/TdCSRrSs.jpeg"},
    {"rank": 15, "name": "Riley Newman", "country": "United States", "age": 31, "points": 6350, "plays": "Right-handed", "profile_image": "https://images.pickleball.com/profile-images/1740596790870/Image_from_iOS__2_-removebg-preview.png"},
    {"rank": 16, "name": "CJ Klinger", "country": "United States", "age": 19, "points": 5350, "plays": "Right-handed", "profile_image": "https://images.pickleball.com/profile-images/1720555787471/qI9e7Vb4.jpeg"},
    {"rank": 17, "name": "James Ignatowich", "country": "United States", "age": 24, "points": 5300, "plays": "Right-handed", "profile_image": "https://images.pickleball.com/profile-images/1739214896862/PPA_MEDIADAY_JAMESIGNATOWICH-4.jpg"},
    {"rank": 18, "name": "Augustus Ge", "country": "United States", "age": 28, "points": 4750, "plays": "Right-handed", "profile_image": "https://images.pickleball.com/profile-images/1720543267349/-MrBM-AA.jpeg"},
    {"rank": 19, "name": "Zane Navratil", "country": "United States", "age": 29, "points": 4700, "plays": "Right-handed", "profile_image": "https://images.pickleball.com/profile-images/1700105256168/Zane-No-Smile.png"},
    {"rank": 20, "name": "Quang Duong", "country": "Vietnam", "age": 19, "points": 4675, "plays": "Right-handed", "profile_image": "https://images.pickleball.com/profile-images/1720553830875/Xj4iEjHU.jpeg"},
    {"rank": 21, "name": "Connor Garnett", "country": "United States", "age": 27, "points": 4600, "plays": "Right-handed", "profile_image": "https://images.pickleball.com/profile-images/1720556594205/RuyQwGSQ.jpeg"},
    {"rank": 22, "name": "Tyler Loong", "country": "United States", "age": 33, "points": 4300, "plays": "Right-handed", "profile_image": "https://images.pickleball.com/profile-images/1720632073291/mlaen7QY.jpeg"},
    {"rank": 23, "name": "Rafa Hewett", "country": "United States", "age": 30, "points": 3350, "plays": "Right-handed", "profile_image": "https://images.pickleball.com/profile-images/1739907629548/b8966189-4517-4dc6-b702-d89581f77ddf.png"},
    {"rank": 24, "name": "Julian Arnold", "country": "United States", "age": 34, "points": 3350, "plays": "Right-handed", "profile_image": "https://images.pickleball.com/profile-images/1720559974997/-3fmaq_s.jpeg"},
    {"rank": 25, "name": "Jay Devilliers", "country": "France", "age": 30, "points": 3150, "plays": "Right-handed", "profile_image": "https://images.pickleball.com/profile-images/1720559759889/E9bf7YzY.jpeg"},
    {"rank": 26, "name": "Travis Rettenmaier", "country": "United States", "age": 41, "points": 3000, "plays": "Right-handed", "profile_image": "https://images.pickleball.com/profile-images/1720632009095/mlaen7QY.jpeg"},
    {"rank": 27, "name": "Hunter Johnson", "country": "United States", "age": 30, "points": 2950, "plays": "Right-handed", "profile_image": "https://images.pickleball.com/profile-images/1720559380285/ZnIbwUds.jpeg"},
    {"rank": 28, "name": "Noe Khlif", "country": "France", "age": 26, "points": 2550, "plays": "Right-handed", "profile_image": "https://images.pickleball.com/profile-images/1720627458524/d8AjhmFw.jpeg"},
    {"rank": 29, "name": "AJ Koller", "country": "United States", "age": 35, "points": 2350, "plays": "Right-handed", "profile_image": "https://images.pickleball.com/profile-images/1738254767164/PPA_MEDIADAY_AJ_KOLLER-18-removebg-preview.png"},
    {"rank": 30, "name": "Patrick Smith", "country": "Germany", "age": 40, "points": 2200, "plays": "Right-handed", "profile_image": "https://images.pickleball.com/profile-images/1720629286320/QLhBqkL4.jpeg"},
    {"rank": 31, "name": "Callan Dawson", "country": "United States", "age": 33, "points": 2175, "plays": "Right-handed", "profile_image": "https://images.pickleball.com/profile-images/1720555660000/SV1-PUTc.jpeg"},
    {"rank": 32, "name": "Darrian Young", "country": "Spain", "age": 24, "points": 2050, "plays": "Right-handed", "profile_image": "https://images.pickleball.com/profile-images/1720558426768/lCJw6yw8.jpeg"},
]

# Women's data (also needed for mixed doubles)
PPA_WOMEN_PLAYERS = [
    {"rank": 1, "name": "Anna Leigh Waters", "country": "United States", "age": 17, "points": 17000, "plays": "Right-handed"},
    {"rank": 2, "name": "Catherine Parenteau", "country": "Canada", "age": 30, "points": 14300, "plays": "Right-handed"},
    {"rank": 3, "name": "Lea Jansen", "country": "United States", "age": 29, "points": 14000, "plays": "Right-handed"},
    {"rank": 4, "name": "Parris Todd", "country": "United States", "age": 27, "points": 13800, "plays": "Right-handed"},
    {"rank": 5, "name": "Salome Devidze", "country": "Georgia", "age": 27, "points": 12900, "plays": "Right-handed"},
    {"rank": 6, "name": "Jorja Johnson", "country": "United States", "age": 19, "points": 12800, "plays": "Right-handed"},
    {"rank": 7, "name": "Etta Wright", "country": "United States", "age": 24, "points": 12500, "plays": "Right-handed"},
    {"rank": 8, "name": "Meghan Dizon", "country": "United States", "age": 26, "points": 9800, "plays": "Right-handed"},
    {"rank": 9, "name": "Vivienne David", "country": "France", "age": 29, "points": 9700, "plays": "Right-handed"},
    {"rank": 10, "name": "Lucy Kovalova", "country": "Slovakia", "age": 33, "points": 9600, "plays": "Right-handed"},
    {"rank": 11, "name": "Lauren Stratman", "country": "United States", "age": 30, "points": 9200, "plays": "Right-handed"},
    {"rank": 12, "name": "Anna Bright", "country": "United States", "age": 24, "points": 9100, "plays": "Right-handed"},
    {"rank": 13, "name": "Jillian Braverman", "country": "United States", "age": 26, "points": 8900, "plays": "Right-handed"},
    {"rank": 14, "name": "Mary Brascia", "country": "United States", "age": 27, "points": 7300, "plays": "Right-handed"},
    {"rank": 15, "name": "Allison Halbert", "country": "United States", "age": 22, "points": 6800, "plays": "Right-handed"},
    {"rank": 16, "name": "Callie Smith", "country": "United States", "age": 28, "points": 5900, "plays": "Right-handed"},
]

# Tournament from tournament.html
TEXAS_OPEN_DETAILS = {
    "name": "CIBC Texas Open",
    "start_date": datetime(2025, 3, 12),
    "end_date": datetime(2025, 3, 16),
    "location": "Courts of McKinney – 3253 Alma Rd McKinney, Texas 75070",
    "venue": "Courts of McKinney",
    "address": "3253 Alma Rd McKinney, Texas 75070",
    "registration_deadline": datetime(2025, 3, 5),
    "status": TournamentStatus.ONGOING,
    "tier": TournamentTier.OPEN,
    "description": "Premier PPA Tour stop in Texas featuring top professional pickleball players.",
    "format": TournamentFormat.SINGLE_ELIMINATION,
    "logo": "https://www.ppatour.com/wp-content/uploads/2024/11/PPA-web-sizes-07.webp",
    "banner": "https://www.ppatour.com/wp-content/uploads/2023/11/2024-tx-open-venue-hero.webp",
    "prize_pool": 150000.0,
    "registration_fee": 200.0
}

def create_admin_and_organizer():
    """Create admin and organizer users"""
    print("Creating admin and organizer users...")
    
    # Create admin user if not exists
    admin = User.query.filter_by(email='admin@example.com').first()
    if not admin:
        admin = User(username='admin', email='admin@example.com', role=UserRole.ADMIN)
        admin.set_password('password')
        db.session.add(admin)
    
    # Create tournament organizer
    organizer = User.query.filter_by(email='organizer@example.com').first()
    if not organizer:
        organizer = User(username='organizer', email='organizer@example.com', role=UserRole.ORGANIZER)
        organizer.set_password('password')
        db.session.add(organizer)
    
    db.session.commit()
    return admin, organizer

def add_ben_johns_details(player_profile):
    """
    Add Ben Johns' details from player_profile.html to a player's profile
    This serves as a template for other players
    """
    # Update basic information
    player_profile.city = "Boca Raton, FL"
    player_profile.bio = "Professional pickleball player and multiple time champion."
    player_profile.height = "6′ 0\""
    player_profile.paddle = "JOOLA Perseus"
    player_profile.profile_image = player_profile.profile_image if hasattr(player_profile, 'profile_image') else None
    player_profile.action_image = "https://www.ppatour.com/wp-content/uploads/2023/06/Ben-Johns-Pickleball.webp"
    player_profile.banner_image = "https://www.ppatour.com/wp-content/uploads/2023/06/3Collin-Ben-scaled-1.webp"
    player_profile.instagram = "https://www.instagram.com/benjohns_pb/"
    player_profile.facebook = "https://www.facebook.com/profile.php?id=100008876373406"
    player_profile.twitter = "https://twitter.com/benjohns_pb"
    player_profile.turned_pro = 2016

    # Add equipment (paddle)
    equipment = Equipment.query.filter_by(player_id=player_profile.id).first()
    if not equipment:
        equipment = Equipment(
            player_id=player_profile.id,
            brand="Joola",
            name="JOOLA Ben Johns Perseus 3S 16mm Pickleball Paddle",
            image="https://www.ppatour.com/wp-content/uploads/2024/03/JOOLA-Ben-Johns-Perseus-3S-16mm-Pickleball-Paddle-Teal-150x150.jpg",
            buy_link="https://pickleballcentral.com/joola-ben-johns-perseus-3s-16mm-pickleball-paddle/"
        )
        db.session.add(equipment)
    
    # Add sponsor
    sponsor = PlayerSponsor.query.filter_by(player_id=player_profile.id).first()
    if not sponsor:
        sponsor = PlayerSponsor(
            player_id=player_profile.id,
            name="JOOLA",
            logo="https://www.ppatour.com/wp-content/uploads/2025/01/JOOLA_Lockup_Horizontal_Outline_Black_RGB.png",
            link="https://www.joolausa.com/"
        )
        db.session.add(sponsor)
    
    db.session.flush()

def create_ppa_players():
    """Create PPA Tour players from the data"""
    print("Creating PPA Tour players...")
    
    male_players = []
    for player_data in PPA_PLAYERS:
        # Create user if not exists
        email = f"{player_data['name'].lower().replace(' ', '.')}@example.com"
        user = User.query.filter_by(email=email).first()
        
        if not user:
            user = User(
                username=player_data['name'].lower().replace(' ', '.'),
                email=email,
                role=UserRole.PLAYER
            )
            user.set_password('password')
            db.session.add(user)
            db.session.flush()  # Ensure user has an ID
        
        # Create or update player profile
        profile = PlayerProfile.query.filter_by(user_id=user.id).first()
        if not profile:
            profile = PlayerProfile(
                user_id=user.id,
                full_name=player_data['name'],
                country=player_data['country'],
                age=player_data['age'],
                plays=player_data['plays'],
                profile_image=player_data.get('profile_image')
            )
            
            # Add rankings points
            profile.mens_singles_points = int(player_data['points'] * 0.8)  # Slightly lower for singles
            profile.mens_doubles_points = player_data['points']
            profile.mixed_doubles_points = int(player_data['points'] * 0.9)  # Slightly lower for mixed
            
            db.session.add(profile)
        else:
            # Update existing profile
            profile.country = player_data['country']
            profile.age = player_data['age']
            profile.plays = player_data['plays']
            profile.profile_image = player_data.get('profile_image')
            profile.mens_singles_points = int(player_data['points'] * 0.8)
            profile.mens_doubles_points = player_data['points']
            profile.mixed_doubles_points = int(player_data['points'] * 0.9)
        
        # Add Ben Johns details to all players as a template
        add_ben_johns_details(profile)
        
        # Store player for later use
        male_players.append(profile)
    
    # Create women players
    female_players = []
    for player_data in PPA_WOMEN_PLAYERS:
        # Create user if not exists
        email = f"{player_data['name'].lower().replace(' ', '.')}@example.com"
        user = User.query.filter_by(email=email).first()
        
        if not user:
            user = User(
                username=player_data['name'].lower().replace(' ', '.'),
                email=email,
                role=UserRole.PLAYER
            )
            user.set_password('password')
            db.session.add(user)
            db.session.flush()  # Ensure user has an ID
        
        # Create or update player profile
        profile = PlayerProfile.query.filter_by(user_id=user.id).first()
        if not profile:
            profile = PlayerProfile(
                user_id=user.id,
                full_name=player_data['name'],
                country=player_data['country'],
                age=player_data['age'],
                plays=player_data['plays']
            )
            
            # Add rankings points
            profile.womens_singles_points = int(player_data['points'] * 0.8)  # Slightly lower for singles
            profile.womens_doubles_points = player_data['points']
            profile.mixed_doubles_points = int(player_data['points'] * 0.9)  # Slightly lower for mixed
            
            db.session.add(profile)
        else:
            # Update existing profile
            profile.country = player_data['country']
            profile.age = player_data['age']
            profile.plays = player_data['plays']
            profile.womens_singles_points = int(player_data['points'] * 0.8)
            profile.womens_doubles_points = player_data['points']
            profile.mixed_doubles_points = int(player_data['points'] * 0.9)
        
        # Add women-specific modifications to the template
        profile.city = "Orlando, FL" if not profile.city else profile.city
        profile.paddle = "Selkirk Invikta" if not profile.paddle else profile.paddle
        profile.instagram = f"https://www.instagram.com/{profile.full_name.lower().replace(' ', '_')}/"
        
        # Store player for later use
        female_players.append(profile)
    
    db.session.commit()
    return {'male': male_players, 'female': female_players}

def create_texas_open(organizer, all_players):
    """Create Texas Open tournament based on tournament.html"""
    print("Creating Texas Open tournament...")
    
    # Create tournament
    tournament = Tournament.query.filter_by(name=TEXAS_OPEN_DETAILS['name']).first()
    if tournament:
        # If tournament already exists, delete it and recreate
        db.session.delete(tournament)
        db.session.commit()
    
    tournament = Tournament(
        name=TEXAS_OPEN_DETAILS['name'],
        organizer_id=organizer.id,
        location=TEXAS_OPEN_DETAILS['location'],
        description=TEXAS_OPEN_DETAILS['description'],
        start_date=TEXAS_OPEN_DETAILS['start_date'],
        end_date=TEXAS_OPEN_DETAILS['end_date'],
        registration_deadline=TEXAS_OPEN_DETAILS['registration_deadline'],
        tier=TEXAS_OPEN_DETAILS['tier'],
        format=TEXAS_OPEN_DETAILS['format'],
        status=TEXAS_OPEN_DETAILS['status'],
        prize_pool=TEXAS_OPEN_DETAILS['prize_pool'],
        registration_fee=TEXAS_OPEN_DETAILS['registration_fee'],
        logo=TEXAS_OPEN_DETAILS['logo'],
        banner=TEXAS_OPEN_DETAILS['banner'],
        is_featured=True  # Mark as featured
    )
    db.session.add(tournament)
    db.session.flush()
    
    # Create categories (men's/women's singles, men's/women's doubles, mixed doubles)
    categories = {}
    
    # Men's singles
    mens_singles = TournamentCategory(
        tournament_id=tournament.id,
        category_type=CategoryType.MENS_SINGLES,
        max_participants=32,
        points_awarded=1800,
        prize_percentage=20.0
    )
    db.session.add(mens_singles)
    categories['mens_singles'] = {'category': mens_singles, 'teams': []}
    
    # Women's singles
    womens_singles = TournamentCategory(
        tournament_id=tournament.id,
        category_type=CategoryType.WOMENS_SINGLES,
        max_participants=32,
        points_awarded=1800,
        prize_percentage=20.0
    )
    db.session.add(womens_singles)
    categories['womens_singles'] = {'category': womens_singles, 'teams': []}
    
    # Men's doubles
    mens_doubles = TournamentCategory(
        tournament_id=tournament.id,
        category_type=CategoryType.MENS_DOUBLES,
        max_participants=32,
        points_awarded=1800,
        prize_percentage=20.0
    )
    db.session.add(mens_doubles)
    categories['mens_doubles'] = {'category': mens_doubles, 'teams': []}
    
    # Women's doubles
    womens_doubles = TournamentCategory(
        tournament_id=tournament.id,
        category_type=CategoryType.WOMENS_DOUBLES,
        max_participants=32,
        points_awarded=1800,
        prize_percentage=20.0
    )
    db.session.add(womens_doubles)
    categories['womens_doubles'] = {'category': womens_doubles, 'teams': []}
    
    # Mixed doubles
    mixed_doubles = TournamentCategory(
        tournament_id=tournament.id,
        category_type=CategoryType.MIXED_DOUBLES,
        max_participants=32,
        points_awarded=1800,
        prize_percentage=20.0
    )
    db.session.add(mixed_doubles)
    categories['mixed_doubles'] = {'category': mixed_doubles, 'teams': []}
    
    db.session.flush()
    
    # Register players based on their rankings
    # Men's singles (Top 16)
    for i, player in enumerate(all_players['male'][:16]):
        reg = Registration(
            player_id=player.id,
            category_id=categories['mens_singles']['category'].id,
            is_approved=True,
            payment_status='paid',
            payment_date=datetime.now() - timedelta(days=7),
            seed=i+1 if i < 8 else None  # Seed top 8 players
        )
        db.session.add(reg)
        categories['mens_singles']['teams'].append(player)
    
    # Women's singles (Top 16)
    for i, player in enumerate(all_players['female'][:16]):
        reg = Registration(
            player_id=player.id,
            category_id=categories['womens_singles']['category'].id,
            is_approved=True,
            payment_status='paid',
            payment_date=datetime.now() - timedelta(days=7),
            seed=i+1 if i < 8 else None  # Seed top 8 players
        )
        db.session.add(reg)
        categories['womens_singles']['teams'].append(player)
    
    # Men's doubles (Top 16 men, 8 teams)
    mens_doubles_teams = form_doubles_teams(all_players['male'][:16])
    for team in mens_doubles_teams:
        player1, player2 = team['players']
        
        # Create team object
        team_obj = Team(
            player1_id=player1.id,
            player2_id=player2.id,
            category_id=categories['mens_doubles']['category'].id
        )
        db.session.add(team_obj)
        db.session.flush()
        categories['mens_doubles']['teams'].append(team_obj)
        
        # Register both players
        reg1 = Registration(
            player_id=player1.id,
            category_id=categories['mens_doubles']['category'].id,
            partner_id=player2.id,
            is_approved=True,
            payment_status='paid',
            payment_date=datetime.now() - timedelta(days=7)
        )
        db.session.add(reg1)
        
        reg2 = Registration(
            player_id=player2.id,
            category_id=categories['mens_doubles']['category'].id,
            partner_id=player1.id,
            is_approved=True,
            payment_status='paid',
            payment_date=datetime.now() - timedelta(days=7)
        )
        db.session.add(reg2)
    
    # Women's doubles (Top 16 women, 8 teams)
    womens_doubles_teams = form_doubles_teams(all_players['female'][:16])
    for team in womens_doubles_teams:
        player1, player2 = team['players']
        
        # Create team object
        team_obj = Team(
            player1_id=player1.id,
            player2_id=player2.id,
            category_id=categories['womens_doubles']['category'].id
        )
        db.session.add(team_obj)
        db.session.flush()
        categories['womens_doubles']['teams'].append(team_obj)
        
        # Register both players
        reg1 = Registration(
            player_id=player1.id,
            category_id=categories['womens_doubles']['category'].id,
            partner_id=player2.id,
            is_approved=True,
            payment_status='paid',
            payment_date=datetime.now() - timedelta(days=7)
        )
        db.session.add(reg1)
        
        reg2 = Registration(
            player_id=player2.id,
            category_id=categories['womens_doubles']['category'].id,
            partner_id=player1.id,
            is_approved=True,
            payment_status='paid',
            payment_date=datetime.now() - timedelta(days=7)
        )
        db.session.add(reg2)
    
    # Mixed doubles (Top 8 men and top 8 women)
    mixed_teams = []
    for i in range(8):
        male_player = all_players['male'][i]
        female_player = all_players['female'][i]
        
        # Create team object
        team_obj = Team(
            player1_id=male_player.id,
            player2_id=female_player.id,
            category_id=categories['mixed_doubles']['category'].id
        )
        db.session.add(team_obj)
        db.session.flush()
        categories['mixed_doubles']['teams'].append(team_obj)
        
        # Register both players
        reg1 = Registration(
            player_id=male_player.id,
            category_id=categories['mixed_doubles']['category'].id,
            partner_id=female_player.id,
            is_approved=True,
            payment_status='paid',
            payment_date=datetime.now() - timedelta(days=7)
        )
        db.session.add(reg1)
        
        reg2 = Registration(
            player_id=female_player.id,
            category_id=categories['mixed_doubles']['category'].id,
            partner_id=male_player.id,
            is_approved=True,
            payment_status='paid',
            payment_date=datetime.now() - timedelta(days=7)
        )
        db.session.add(reg2)
    
    # Create and set up initial bracket matches for all categories
    for category_key, category_data in categories.items():
        create_initial_tournament_bracket(tournament, category_data['category'], category_data['teams'])
    
    db.session.commit()
    return tournament, categories

def form_doubles_teams(players):
    """Form doubles teams from players, preserving original functionality"""
    random.shuffle(players)
    teams = []
    
    # Group players by continent/region
    regions = {
        "North America": ["United States", "Canada"],
        "South America": ["Brazil", "Argentina", "Colombia", "Bolivia"],
        "Europe": ["United Kingdom", "Spain", "France", "Germany", "Romania"],
        "Middle East": ["Israel"],
        "Asia": ["China", "Japan", "South Korea", "Vietnam"],
        "Oceania": ["Australia", "New Zealand"]
    }
    
    # Group players by region
    players_by_region = {}
    for region, countries in regions.items():
        players_by_region[region] = [p for p in players if p.country in countries]
    
    # Try to form teams from the same region when possible
    for region, regional_players in players_by_region.items():
        # Form as many teams as possible from this region
        for i in range(0, len(regional_players) - 1, 2):
            if len(regional_players) > i+1:
                teams.append((regional_players[i], regional_players[i+1]))
                # Mark these players as assigned
                if regional_players[i] in players:
                    players.remove(regional_players[i])
                if regional_players[i+1] in players:
                    players.remove(regional_players[i+1])
    
    # For any remaining players, just pair them up
    for i in range(0, len(players) - 1, 2):
        if len(players) > i+1:
            teams.append((players[i], players[i+1]))
    
    # Name the teams based on player last names
    named_teams = []
    for player1, player2 in teams:
        last_name1 = player1.full_name.split()[-1]
        last_name2 = player2.full_name.split()[-1]
        
        # Combine last names alphabetically
        if last_name1 < last_name2:
            team_name = f"{last_name1}/{last_name2}"
        else:
            team_name = f"{last_name2}/{last_name1}"
            
        named_teams.append({
            'name': team_name,
            'players': (player1, player2)
        })
    
    return named_teams

def create_initial_tournament_bracket(tournament, category, participants):
    """Create initial bracket matches for a tournament in progress"""
    # For an ongoing tournament, we'll create the full bracket structure,
    # but only simulate matches in the early rounds
    
    # Get MatchStage enum if it exists
    match_stage = MatchStage.KNOCKOUT if 'MatchStage' in globals() else None
    
    # Determine bracket size based on number of participants
    bracket_size = 1
    while bracket_size < len(participants):
        bracket_size *= 2
    
    # Add byes to fill bracket if needed
    while len(participants) < bracket_size:
        participants.append(None)
    
    # For seeding, ensure top players are spread across the bracket
    seeded_participants = []
    
    # Take the top quarter of participants as seeds
    seed_count = max(1, len(participants) // 4)
    seeds = participants[:seed_count]
    remaining = participants[seed_count:]
    random.shuffle(remaining)
    
    # Place seeds according to standard tournament seeding pattern
    if len(seeds) >= 1:
        # First seed goes at the top
        seeded_participants.append(seeds[0])
        
    if len(seeds) >= 2:
        # Second seed goes at the bottom
        seeded_participants.append(None)  # Placeholder
        seeded_participants[-1] = seeds[1]
    
    if len(seeds) >= 4:
        # Seeds 3-4 go in the middle sections
        quarter_point = len(participants) // 4
        seeded_participants.insert(quarter_point, seeds[2])
        seeded_participants.insert(3 * quarter_point, seeds[3])
    
    # Fill in the rest of the bracket with non-seeded participants
    for i in range(len(seeded_participants), bracket_size):
        if remaining:
            seeded_participants.insert(i, remaining.pop(0))
        else:
            seeded_participants.insert(i, None)  # Bye
    
    # Create round 1 matches (first round)
    round_matches = []
    round_number = int(bracket_size / 2).bit_length()  # Calculate round number from bracket size
    
    for i in range(0, len(seeded_participants), 2):
        participant1 = seeded_participants[i]
        participant2 = seeded_participants[i+1] if i+1 < len(seeded_participants) else None
        
        if not participant1 and not participant2:
            continue  # Skip match if both participants are byes
        
        # Create match
        match_kwargs = {
            'category_id': category.id,
            'round': round_number,
            'match_order': i // 2,
            'court': f"Court {random.randint(1, 8)}",
            'scheduled_time': tournament.start_date + timedelta(hours=random.randint(1, 8))
        }
        
        # For an ongoing tournament, first round matches might be completed
        should_complete = random.random() < 0.7  # 70% of first round matches are completed
        match_kwargs['completed'] = should_complete
        
        # Add stage if the match has this field
        if match_stage:
            match_kwargs['stage'] = match_stage
        
        # Add team/player IDs based on category type
        if category.is_doubles():
            if participant1:
                match_kwargs['team1_id'] = participant1.id
            if participant2:
                match_kwargs['team2_id'] = participant2.id
        else:
            if participant1:
                match_kwargs['player1_id'] = participant1.id
            if participant2:
                match_kwargs['player2_id'] = participant2.id
        
        match = Match(**match_kwargs)
        db.session.add(match)
        db.session.flush()
        
        # If match is completed, simulate scores
        if should_complete and participant1 and participant2:
            if category.is_doubles():
                simulate_doubles_match_score(match, participant1, participant2)
                winner = participant1 if match.winning_team_id == participant1.id else participant2
            else:
                simulate_singles_match_score(match, participant1, participant2)
                winner = participant1 if match.winning_player_id == participant1.id else participant2
            round_matches.append((match, winner))
        else:
            round_matches.append((match, None))
    
    # Create future round matches
    next_round_number = round_number - 1
    next_round_matches = []
    
    while next_round_number >= 1:
        for i in range(0, len(round_matches), 2):
            if i+1 < len(round_matches):
                match1, winner1 = round_matches[i]
                match2, winner2 = round_matches[i+1]
                
                # Create next round match
                match_kwargs = {
                    'category_id': category.id,
                    'round': next_round_number,
                    'match_order': i // 2,
                    'court': f"Court {random.randint(1, 4)}",
                    'scheduled_time': tournament.start_date + timedelta(days=1, hours=random.randint(1, 8))
                }
                
                # For an ongoing tournament, second round might be partially completed
                should_complete = next_round_number >= 3 and random.random() < 0.3  # 30% of second round+ are completed
                match_kwargs['completed'] = should_complete
                
                # Add stage if the match has this field
                if match_stage:
                    match_kwargs['stage'] = match_stage
                
                match = Match(**match_kwargs)
                
                # Link with previous round matches
                if match1:
                    match1.next_match_id = match.id
                if match2:
                    match2.next_match_id = match.id
                
                # If both previous matches have winners and this match should be completed
                if should_complete and winner1 and winner2:
                    if category.is_doubles():
                        match.team1_id = winner1.id
                        match.team2_id = winner2.id
                        simulate_doubles_match_score(match, winner1, winner2)
                        next_winner = winner1 if match.winning_team_id == winner1.id else winner2
                    else:
                        match.player1_id = winner1.id
                        match.player2_id = winner2.id
                        simulate_singles_match_score(match, winner1, winner2)
                        next_winner = winner1 if match.winning_player_id == winner1.id else winner2
                    
                    db.session.add(match)
                    db.session.flush()
                    next_round_matches.append((match, next_winner))
                else:
                    # If match is not completed or we don't have both winners
                    # we'll still create the match structure for the bracket
                    if winner1:
                        if category.is_doubles():
                            match.team1_id = winner1.id
                        else:
                            match.player1_id = winner1.id
                    
                    if winner2:
                        if category.is_doubles():
                            match.team2_id = winner2.id
                        else:
                            match.player2_id = winner2.id
                    
                    db.session.add(match)
                    db.session.flush()
                    next_round_matches.append((match, None))
        
        round_matches = next_round_matches
        next_round_matches = []
        next_round_number -= 1
    
    db.session.commit()

def create_completed_tournament(organizer, all_players):
    """Create a comprehensive test tournament with multiple categories and formats (from original seed.py)"""
    print("Creating completed tournament...")
    
    # Create tournament
    tournament = Tournament.query.filter_by(name='Rocky Mountain Championship').first()
    if tournament:
        # If tournament already exists, delete it and recreate
        db.session.delete(tournament)
        db.session.commit()
    
    start_date = datetime.now() - timedelta(days=14)  # 2 weeks ago
    end_date = start_date + timedelta(days=3)
    registration_deadline = start_date - timedelta(days=7)
    
    tournament = Tournament(
        name='Rocky Mountain Championship',
        organizer_id=organizer.id,
        location='Denver, Colorado',
        description='A premier pickleball tournament featuring multiple categories and formats.',
        start_date=start_date,
        end_date=end_date,
        registration_deadline=registration_deadline,
        tier=TournamentTier.OPEN,
        format=TournamentFormat.GROUP_KNOCKOUT,  # Default format, individual categories can override
        status=TournamentStatus.COMPLETED,  # Set as completed for this example
        prize_pool=20000.0,
        registration_fee=150.0
    )
    db.session.add(tournament)
    db.session.flush()
    
    # Create categories with different formats and prize distributions
    categories = create_tournament_categories(tournament, all_players)
    
    # Register players and create teams
    print("Registering players and creating teams...")
    register_players_and_create_teams(categories, all_players)

    # Create matches for all categories
    print("Creating matches for all categories...")
    for category_key, category_data in categories.items():
        if category_data['format'] == TournamentFormat.GROUP_KNOCKOUT:
            print(f"Creating group stage for {category_key}...")
            # Store the returned groups in the category_data instead of directly in the category
            category_data['groups'] = create_group_stage_matches(tournament, category_data['category'], category_data['teams'])
            print(f"Creating knockout stage for {category_key}...")
            create_knockout_stage(tournament, category_data['category'], category_data['groups'])
        else:
            # Single elimination format
            print(f"Creating single elimination bracket for {category_key}...")
            create_single_elimination_bracket(tournament, category_data['category'], category_data['teams'])
    
    # Calculate prize money for each category based on percentage
    for category_key, category_data in categories.items():
        category = category_data['category']
        if hasattr(category, 'prize_percentage') and hasattr(category, 'prize_money'):
            category.prize_money = tournament.prize_pool * (category.prize_percentage / 100)
            db.session.flush()
    
    # Calculate final placings and distribute prizes using service layer if available
    if SERVICES_AVAILABLE:
        print("Calculating final placings and distributing prizes using service layer...")
        try:
            # Try to distribute prize money first
            PrizeService.distribute_prize_pool(tournament.id)
            
            for category_key, category_data in categories.items():
                try:
                    placings = PlacingService.get_placings(category_data['category'].id)
                    print(f"Calculated {len(placings)} placings for {category_key}")
                    if len(placings) > 0:
                        category_data['placings'] = placings
                except Exception as e:
                    print(f"Error calculating placings for {category_key}: {str(e)}")
        except Exception as e:
            print(f"Error distributing prize money: {str(e)}")
    
    # Commit any pending changes
    db.session.commit()
    
    return tournament, categories

def create_tournament_categories(tournament, all_players):
    """Create a mix of tournament categories with different formats and prize distributions"""
    # Prepare the categories data structure
    categories = {}
    
    # Create men's doubles - GROUP + KNOCKOUT format
    mens_doubles = TournamentCategory(
        tournament_id=tournament.id,
        category_type=CategoryType.MENS_DOUBLES,
        max_participants=16,
        points_awarded=1400,
        prize_percentage=30.0,  # 30% of total prize pool
        format= TournamentFormat.GROUP_KNOCKOUT
    )
    
    # Add new fields if they exist
    if hasattr(TournamentCategory, 'group_count'):
        mens_doubles.group_count = 4
        mens_doubles.teams_per_group = 4
        mens_doubles.teams_advancing_per_group = 2
    
    # Add custom prize distribution if the field exists
    if hasattr(TournamentCategory, 'prize_distribution'):
        mens_doubles.prize_distribution = {
            "1": 50,
            "2": 25,
            "3-4": 12.5,
        }
    
    # Add custom points distribution if the field exists
    if hasattr(TournamentCategory, 'points_distribution'):
        mens_doubles.points_distribution = {
            "1": 100,
            "2": 70,
            "3-4": 50,
            "5-8": 25,
        }
    
    db.session.add(mens_doubles)
    db.session.flush()
    
    # Add to categories data structure
    categories['mens_doubles'] = {
        'category': mens_doubles,
        'format': TournamentFormat.GROUP_KNOCKOUT,
        'teams': [],
        'groups': []
    }
    
    # Create women's singles - SINGLE ELIMINATION format
    womens_singles = TournamentCategory(
        tournament_id=tournament.id,
        category_type=CategoryType.WOMENS_SINGLES,
        max_participants=16,
        points_awarded=1200,
        prize_percentage=20.0,  # 20% of total prize pool
        format= TournamentFormat.SINGLE_ELIMINATION
    )
    
    # Add custom prize distribution if the field exists
    if hasattr(TournamentCategory, 'prize_distribution'):
        womens_singles.prize_distribution = {
            "1": 60,
            "2": 30,
            "3-4": 5,
        }
    
    db.session.add(womens_singles)
    db.session.flush()
    
    # Add to categories data structure
    categories['womens_singles'] = {
        'category': womens_singles,
        'format': TournamentFormat.SINGLE_ELIMINATION,
        'teams': [],
        'groups': []
    }
    
    # Create mixed doubles - SINGLE ELIMINATION format
    mixed_doubles = TournamentCategory(
        tournament_id=tournament.id,
        category_type=CategoryType.MIXED_DOUBLES,
        max_participants=16,
        points_awarded=1300,
        prize_percentage=30.0,  # 30% of total prize pool
        format= TournamentFormat.SINGLE_ELIMINATION
    )
    
    # Add custom prize distribution if the field exists
    if hasattr(TournamentCategory, 'prize_distribution'):
        mixed_doubles.prize_distribution = {
            "1": 50,
            "2": 25,
            "3-4": 12.5,
        }
    
    db.session.add(mixed_doubles)
    db.session.flush()
    
    # Add to categories data structure
    categories['mixed_doubles'] = {
        'category': mixed_doubles,
        'format': TournamentFormat.SINGLE_ELIMINATION,
        'teams': [],
        'groups': []
    }
    
    # Create men's singles - SINGLE ELIMINATION with DUPR restrictions
    mens_singles = TournamentCategory(
        tournament_id=tournament.id,
        category_type=CategoryType.MENS_SINGLES,
        max_participants=16,
        points_awarded=1200,
        prize_percentage=20.0,  # 20% of total prize pool
        format= TournamentFormat.SINGLE_ELIMINATION
    )
    
    # Add DUPR restrictions if the fields exist
    if hasattr(TournamentCategory, 'min_dupr_rating'):
        mens_singles.min_dupr_rating = 4.0
        mens_singles.max_dupr_rating = 5.5
    
    db.session.add(mens_singles)
    db.session.flush()
    
    # Add to categories data structure
    categories['mens_singles'] = {
        'category': mens_singles,
        'format': TournamentFormat.SINGLE_ELIMINATION,
        'teams': [],
        'groups': []
    }
    
    db.session.commit()
    return categories

# The following functions are kept from the original seed.py
# Only including function signatures as a reminder - the implementations
# remain unchanged from the original
def register_players_and_create_teams(categories, all_players):
    """Register players to categories and create teams"""
    # Code unchanged from original seed.py
    # Men's Doubles - Form teams and register 16 teams
    mens_doubles_teams = form_doubles_teams(all_players['male'][:32])

    for team in mens_doubles_teams[:16]:  # Limit to 16 teams
        player1, player2 = team['players']
        
        # Create team object
        team_obj = Team(
            player1_id=player1.id,
            player2_id=player2.id,
            category_id=categories['mens_doubles']['category'].id
        )
        db.session.add(team_obj)
        db.session.flush()
        categories['mens_doubles']['teams'].append(team_obj)
        
        # Register both players
        reg1 = Registration(
            player_id=player1.id,
            category_id=categories['mens_doubles']['category'].id,
            partner_id=player2.id,
            is_approved=True,
            payment_status='paid',
            payment_date=datetime.now() - timedelta(days=14)
        )
        db.session.add(reg1)
        
        reg2 = Registration(
            player_id=player2.id,
            category_id=categories['mens_doubles']['category'].id,
            partner_id=player1.id,
            is_approved=True,
            payment_status='paid',
            payment_date=datetime.now() - timedelta(days=14)
        )
        db.session.add(reg2)
    
    # Women's Singles - Register 8 female players
    for i, player in enumerate(all_players['female'][:8]):
        # Register player
        reg = Registration(
            player_id=player.id,
            category_id=categories['womens_singles']['category'].id,
            is_approved=True,
            payment_status='paid',
            payment_date=datetime.now() - timedelta(days=14),
            seed=i+1 if i < 4 else None  # Seed top 4 players
        )
        db.session.add(reg)
        categories['womens_singles']['teams'].append(player)
    
    # Mixed Doubles - Form 8 mixed teams
    for i in range(8):
        # Pair male and female players
        male_player = all_players['male'][i]
        female_player = all_players['female'][i]
        
        # Create team object
        team_obj = Team(
            player1_id=male_player.id,
            player2_id=female_player.id,
            category_id=categories['mixed_doubles']['category'].id
        )
        db.session.add(team_obj)
        db.session.flush()
        categories['mixed_doubles']['teams'].append(team_obj)
        
        # Register both players
        reg1 = Registration(
            player_id=male_player.id,
            category_id=categories['mixed_doubles']['category'].id,
            partner_id=female_player.id,
            is_approved=True,
            payment_status='paid',
            payment_date=datetime.now() - timedelta(days=14)
        )
        db.session.add(reg1)
        
        reg2 = Registration(
            player_id=female_player.id,
            category_id=categories['mixed_doubles']['category'].id,
            partner_id=male_player.id,
            is_approved=True,
            payment_status='paid',
            payment_date=datetime.now() - timedelta(days=14)
        )
        db.session.add(reg2)
    
    # Men's Singles - Register 8 male players
    for i, player in enumerate(all_players['male'][16:24]):
        # Register player
        reg = Registration(
            player_id=player.id,
            category_id=categories['mens_singles']['category'].id,
            is_approved=True,
            payment_status='paid',
            payment_date=datetime.now() - timedelta(days=14),
            seed=i+1 if i < 4 else None  # Seed top 4 players
        )
        db.session.add(reg)
        categories['mens_singles']['teams'].append(player)
    
    db.session.commit()

def create_group_stage_matches(tournament, category, teams):
    """Create and simulate group stage matches for a category"""
    # Code unchanged from original seed.py
    # Set up groups
    random.shuffle(teams)
    
    # Create 4 groups with teams
    group_count = getattr(category, 'group_count', 4)
    teams_per_group = getattr(category, 'teams_per_group', 4)
    
    groups = []
    for i in range(group_count):
        start_idx = i * teams_per_group
        end_idx = start_idx + teams_per_group
        if start_idx >= len(teams):
            continue
            
        group_teams = teams[start_idx:min(end_idx, len(teams))]
        
        # Create Group object if model exists
        group = None
        if 'Group' in globals():
            group = Group(
                category_id=category.id,
                name=chr(65 + i)  # A, B, C, D, etc.
            )
            db.session.add(group)
            db.session.flush()
        
        groups.append({
            'name': f'Group {chr(65 + i)}',  # Group A, B, C, D, etc.
            'group': group,
            'teams': group_teams,
            'advancing': []
        })
    
    # Get MatchStage enum if it exists
    match_stage = MatchStage.GROUP if 'MatchStage' in globals() else None
    round_number = 4  # Use round 4 for group stage
    match_order = 0
    
    for group_idx, group in enumerate(groups):
        group_teams = group['teams']
        
        # Create matches between teams in the group
        for i in range(len(group_teams)):
            for j in range(i + 1, len(group_teams)):
                team1 = group_teams[i]
                team2 = group_teams[j]
                
                # Create match
                match_kwargs = {
                    'category_id': category.id,
                    'round': round_number,
                    'match_order': (group_idx * 10) + match_order,  # Group ID in tens digit
                    'completed': True,
                    'court': f"Court {random.randint(1, 8)}"
                }
                
                # Add group_id if the match has this field
                if group.get('group'):
                    match_kwargs['group_id'] = group['group'].id
                
                # Add stage if the match has this field
                if match_stage:
                    match_kwargs['stage'] = match_stage
                
                # Add team IDs based on whether this is singles or doubles
                if category.is_doubles():
                    match_kwargs['team1_id'] = team1.id
                    match_kwargs['team2_id'] = team2.id
                else:
                    match_kwargs['player1_id'] = team1.id
                    match_kwargs['player2_id'] = team2.id
                
                match = Match(**match_kwargs)
                db.session.add(match)
                db.session.flush()
                
                # Simulate match score
                if category.is_doubles():
                    simulate_doubles_match_score(match, team1, team2)
                else:
                    simulate_singles_match_score(match, team1, team2)
                
                match_order += 1

    db.session.commit()
    
    # Calculate group standings
    for group in groups:
        # Get detailed standings including stats, not just team order
        detailed_standings = []
        
        if category.is_doubles():
            # Modify calculate_doubles_group_standings to return full stats
            detailed_standings = calculate_doubles_group_standings_with_stats(group['teams'], category)
            # Set the list of teams for advancing
            team_order = [s['team'] for s in detailed_standings]
        else:
            # Modify calculate_singles_group_standings to return full stats
            detailed_standings = calculate_singles_group_standings_with_stats(group['teams'], category)
            # Set the list of teams for advancing
            team_order = [s['player'] for s in detailed_standings]
        
        # Top teams advance from each group
        teams_advancing = getattr(category, 'teams_advancing_per_group', 2)
        teams_advancing = min(teams_advancing, len(team_order))
        group['advancing'] = team_order[:teams_advancing]
        
        # Create GroupStanding objects if using the new model
        if 'GroupStanding' in globals() and group.get('group'):
            for i, standing_data in enumerate(detailed_standings):
                standing_kwargs = {
                    'group_id': group['group'].id,
                    'position': i + 1,
                    'matches_played': standing_data['matches'],
                    'matches_won': standing_data['wins'],
                    'matches_lost': standing_data['matches'] - standing_data['wins'],
                    'sets_won': standing_data['sets_won'],
                    'sets_lost': standing_data['sets_lost'],
                    'points_won': standing_data.get('points_won', 0),  # May not be present in original
                    'points_lost': standing_data.get('points_lost', 0)  # May not be present in original
                }
                
                # Add team/player ID based on category type
                if category.is_doubles():
                    standing_kwargs['team_id'] = standing_data['team'].id
                else:
                    standing_kwargs['player_id'] = standing_data['player'].id
                
                standing = GroupStanding(**standing_kwargs)
                db.session.add(standing)
    
    db.session.commit()
    
    # Return the groups data for use in other functions
    return groups

def calculate_doubles_group_standings_with_stats(teams, category):
    """Calculate group standings for doubles teams with full stats"""
    # Code unchanged from original seed.py
    standings = []
    
    for team in teams:
        # Get all matches involving this team
        matches_team1 = Match.query.filter_by(
            category_id=category.id, 
            team1_id=team.id,
            completed=True
        ).all()
        
        matches_team2 = Match.query.filter_by(
            category_id=category.id, 
            team2_id=team.id,
            completed=True
        ).all()
        
        wins = 0
        total_matches = len(matches_team1) + len(matches_team2)
        sets_won = 0
        sets_lost = 0
        points_won = 0
        points_lost = 0
        
        # Process matches where team was team1
        for match in matches_team1:
            if match.winning_team_id == team.id:
                wins += 1
            
            # Count sets and points
            for score in match.scores:
                if score.player1_score > score.player2_score:
                    sets_won += 1
                else:
                    sets_lost += 1
                
                points_won += score.player1_score
                points_lost += score.player2_score
        
        # Process matches where team was team2
        for match in matches_team2:
            if match.winning_team_id == team.id:
                wins += 1
            
            # Count sets and points
            for score in match.scores:
                if score.player2_score > score.player1_score:
                    sets_won += 1
                else:
                    sets_lost += 1
                
                points_won += score.player2_score
                points_lost += score.player1_score
        
        # Calculate set differential
        set_diff = sets_won - sets_lost
        point_diff = points_won - points_lost
        
        standings.append({
            'team': team,
            'wins': wins,
            'matches': total_matches,
            'sets_won': sets_won,
            'sets_lost': sets_lost,
            'set_diff': set_diff,
            'points_won': points_won,
            'points_lost': points_lost,
            'point_diff': point_diff
        })
    
    # Sort by wins, then set differential, then point differential
    standings.sort(key=lambda x: (x['wins'], x['set_diff'], x['point_diff']), reverse=True)
    
    return standings

def calculate_singles_group_standings_with_stats(players, category):
    """Calculate group standings for singles players with full stats"""
    # Code unchanged from original seed.py
    standings = []
    
    for player in players:
        # Get all matches involving this player
        matches_player1 = Match.query.filter_by(
            category_id=category.id, 
            player1_id=player.id,
            completed=True
        ).all()
        
        matches_player2 = Match.query.filter_by(
            category_id=category.id, 
            player2_id=player.id,
            completed=True
        ).all()
        
        wins = 0
        total_matches = len(matches_player1) + len(matches_player2)
        sets_won = 0
        sets_lost = 0
        points_won = 0
        points_lost = 0
        
        # Process matches where player was player1
        for match in matches_player1:
            if match.winning_player_id == player.id:
                wins += 1
            
            # Count sets and points
            for score in match.scores:
                if score.player1_score > score.player2_score:
                    sets_won += 1
                else:
                    sets_lost += 1
                
                points_won += score.player1_score
                points_lost += score.player2_score
        
        # Process matches where player was player2
        for match in matches_player2:
            if match.winning_player_id == player.id:
                wins += 1
            
            # Count sets and points
            for score in match.scores:
                if score.player2_score > score.player1_score:
                    sets_won += 1
                else:
                    sets_lost += 1
                
                points_won += score.player2_score
                points_lost += score.player1_score
        
        # Calculate set differential
        set_diff = sets_won - sets_lost
        point_diff = points_won - points_lost
        
        standings.append({
            'player': player,
            'wins': wins,
            'matches': total_matches,
            'sets_won': sets_won,
            'sets_lost': sets_lost,
            'set_diff': set_diff,
            'points_won': points_won,
            'points_lost': points_lost,
            'point_diff': point_diff
        })
    
    # Sort by wins, then set differential, then point differential
    standings.sort(key=lambda x: (x['wins'], x['set_diff'], x['point_diff']), reverse=True)
    
    return standings

def create_knockout_stage(tournament, category, groups):
    """Create and simulate knockout stage matches for a category"""
    # Code unchanged from original seed.py
    # Get MatchStage enum if it exists
    match_stage = MatchStage.KNOCKOUT if 'MatchStage' in globals() else None
    
    # Extract advancing teams from each group
    advancing_teams = []
    for group in groups:
        if len(group['advancing']) >= 2:
            advancing_teams.extend(group['advancing'][:2])
        else:
            # If a group doesn't have 2 advancing teams, use what's available
            advancing_teams.extend(group['advancing'])
    
    print(f"Teams advancing to knockout stage: {len(advancing_teams)}")
    
    # Make sure we have enough teams for quarterfinals
    if len(advancing_teams) < 8:
        print(f"Warning: Only {len(advancing_teams)} teams advancing, adding byes as needed")
        # Add None values for byes
        advancing_teams.extend([None] * (8 - len(advancing_teams)))
    
    # Set up quarterfinals - Cross-group seeding
    # A1 vs D2, B1 vs C2, C1 vs B2, D1 vs A2
    quarterfinal_matches = [
        (advancing_teams[0], advancing_teams[7]) if len(advancing_teams) > 7 else (advancing_teams[0], None),
        (advancing_teams[2], advancing_teams[5]) if len(advancing_teams) > 5 else (advancing_teams[2], None),
        (advancing_teams[4], advancing_teams[3]) if len(advancing_teams) > 4 else (advancing_teams[4], None),
        (advancing_teams[6], advancing_teams[1]) if len(advancing_teams) > 6 else (advancing_teams[6], None),
    ]
    
    # Create quarterfinal matches
    quarterfinal_winners = []
    for i, (team1, team2) in enumerate(quarterfinal_matches):
        # Skip if either team is None (bye)
        if team1 is None or team2 is None:
            winner = team1 if team1 is not None else team2
            quarterfinal_winners.append(winner)
            continue
            
        # Create match
        match_kwargs = {
            'category_id': category.id,
            'round': 3,  # Round 3 for quarterfinals
            'match_order': i,
            'completed': True,
            'court': f"Court {i+1}"
        }
        
        # Add stage if the match has this field
        if match_stage:
            match_kwargs['stage'] = match_stage
        
        # Add team/player IDs based on category type
        if category.is_doubles():
            match_kwargs['team1_id'] = team1.id
            match_kwargs['team2_id'] = team2.id
        else:
            match_kwargs['player1_id'] = team1.id
            match_kwargs['player2_id'] = team2.id
        
        match = Match(**match_kwargs)
        db.session.add(match)
        db.session.flush()
        
        # Simulate match
        if category.is_doubles():
            simulate_doubles_match_score(match, team1, team2)
            # Determine winner
            winner = team1 if match.winning_team_id == team1.id else team2
        else:
            simulate_singles_match_score(match, team1, team2)
            # Determine winner
            winner = team1 if match.winning_player_id == team1.id else team2
        
        quarterfinal_winners.append(winner)
    
    # Set up semifinals - Quarterfinal winners play each other
    semifinal_matches = [
        (quarterfinal_winners[0], quarterfinal_winners[1]),  # QF1 vs QF2
        (quarterfinal_winners[2], quarterfinal_winners[3]),  # QF3 vs QF4
    ]
    
    # Create semifinal matches
    semifinal_winners = []
    semifinal_losers = []  # Keep track for 3rd place match
    
    for i, (team1, team2) in enumerate(semifinal_matches):
        # Skip if either team is None (bye)
        if team1 is None or team2 is None:
            winner = team1 if team1 is not None else team2
            semifinal_winners.append(winner)
            continue
            
        # Create match
        match_kwargs = {
            'category_id': category.id,
            'round': 2,  # Round 2 for semifinals
            'match_order': i,
            'completed': True,
            'court': "Center Court" if i == 0 else "Court 1"
        }
        
        # Add stage if the match has this field
        if match_stage:
            match_kwargs['stage'] = match_stage
        
        # Add team/player IDs based on category type
        if category.is_doubles():
            match_kwargs['team1_id'] = team1.id
            match_kwargs['team2_id'] = team2.id
        else:
            match_kwargs['player1_id'] = team1.id
            match_kwargs['player2_id'] = team2.id
        
        match = Match(**match_kwargs)
        db.session.add(match)
        db.session.flush()
        
        # Simulate match
        if category.is_doubles():
            simulate_doubles_match_score(match, team1, team2)
            # Determine winner and loser
            if match.winning_team_id == team1.id:
                winner, loser = team1, team2
            else:
                winner, loser = team2, team1
        else:
            simulate_singles_match_score(match, team1, team2)
            # Determine winner and loser
            if match.winning_player_id == team1.id:
                winner, loser = team1, team2
            else:
                winner, loser = team2, team1
        
        semifinal_winners.append(winner)
        semifinal_losers.append(loser)
    
    # Create final match
    if len(semifinal_winners) >= 2 and semifinal_winners[0] is not None and semifinal_winners[1] is not None:
        final_kwargs = {
            'category_id': category.id,
            'round': 1,  # Round 1 for final
            'match_order': 0,
            'completed': True,
            'court': "Center Court"
        }
        
        # Add stage if the match has this field
        if match_stage:
            final_kwargs['stage'] = match_stage
        
        # Add team/player IDs based on category type
        if category.is_doubles():
            final_kwargs['team1_id'] = semifinal_winners[0].id
            final_kwargs['team2_id'] = semifinal_winners[1].id
        else:
            final_kwargs['player1_id'] = semifinal_winners[0].id
            final_kwargs['player2_id'] = semifinal_winners[1].id
        
        final = Match(**final_kwargs)
        db.session.add(final)
        db.session.flush()
        
        # Simulate final
        if category.is_doubles():
            simulate_doubles_match_score(final, semifinal_winners[0], semifinal_winners[1])
        else:
            simulate_singles_match_score(final, semifinal_winners[0], semifinal_winners[1])
    
    # Create 3rd place match if supported
    playoff_stage = MatchStage.PLAYOFF if 'MatchStage' in globals() else None
    if playoff_stage and len(semifinal_losers) == 2 and semifinal_losers[0] is not None and semifinal_losers[1] is not None:
        playoff_kwargs = {
            'category_id': category.id,
            'round': 1.5,  # Round 1.5 for 3rd place match
            'match_order': 0,
            'completed': True,
            'court': "Court 1",
            'stage': playoff_stage
        }
        
        # Add team/player IDs based on category type
        if category.is_doubles():
            playoff_kwargs['team1_id'] = semifinal_losers[0].id
            playoff_kwargs['team2_id'] = semifinal_losers[1].id
        else:
            playoff_kwargs['player1_id'] = semifinal_losers[0].id
            playoff_kwargs['player2_id'] = semifinal_losers[1].id
        
        playoff = Match(**playoff_kwargs)
        db.session.add(playoff)
        db.session.flush()
        
        # Simulate 3rd place match
        if category.is_doubles():
            simulate_doubles_match_score(playoff, semifinal_losers[0], semifinal_losers[1])
        else:
            simulate_singles_match_score(playoff, semifinal_losers[0], semifinal_losers[1])
    
    db.session.commit()

def create_single_elimination_bracket(tournament, category, participants):
    """Create and simulate single elimination bracket matches"""
    # Code unchanged from original seed.py
    # Get MatchStage enum if it exists
    match_stage = MatchStage.KNOCKOUT if 'MatchStage' in globals() else None
    
    # Determine bracket size based on number of participants
    bracket_size = 1
    while bracket_size < len(participants):
        bracket_size *= 2
    
    # Add byes to fill bracket if needed
    while len(participants) < bracket_size:
        participants.append(None)
    
    # Shuffle participants for random seeding
    random.shuffle(participants)
    
    # Create rounds
    rounds = {}
    rounds[3] = []  # Quarterfinals
    rounds[2] = []  # Semifinals
    rounds[1] = []  # Finals
    
    # Create quarterfinal matches
    for i in range(0, len(participants), 2):
        if i + 1 < len(participants):
            participant1 = participants[i]
            participant2 = participants[i+1]
            
            if not participant1 or not participant2:
                continue  # Skip match if either participant is a bye
            
            # Create match
            match_kwargs = {
                'category_id': category.id,
                'round': 3,  # Round 3 for quarterfinals
                'match_order': i // 2,
                'completed': True,
                'court': f"Court {random.randint(1, 4)}"
            }
            
            # Add stage if the match has this field
            if match_stage:
                match_kwargs['stage'] = match_stage
            
            # Add team/player IDs based on category type
            if category.is_doubles():
                match_kwargs['team1_id'] = participant1.id
                match_kwargs['team2_id'] = participant2.id
            else:
                match_kwargs['player1_id'] = participant1.id
                match_kwargs['player2_id'] = participant2.id
            
            match = Match(**match_kwargs)
            db.session.add(match)
            db.session.flush()
            
            # Simulate match score
            if category.is_doubles():
                simulate_doubles_match_score(match, participant1, participant2)
                # Add to quarterfinals round
                rounds[3].append({
                    'match': match,
                    'winner': participant1 if match.winning_team_id == participant1.id else participant2
                })
            else:
                simulate_singles_match_score(match, participant1, participant2)
                # Add to quarterfinals round
                rounds[3].append({
                    'match': match,
                    'winner': participant1 if match.winning_player_id == participant1.id else participant2
                })
    
    # Create semifinal matches
    for i in range(0, len(rounds[3]), 2):
        if i+1 < len(rounds[3]):
            participant1 = rounds[3][i]['winner']
            participant2 = rounds[3][i+1]['winner']
            
            # Create match
            match_kwargs = {
                'category_id': category.id,
                'round': 2,  # Round 2 for semifinals
                'match_order': i // 2,
                'completed': True,
                'court': "Center Court" if i == 0 else "Court 1"
            }
            
            # Add stage if the match has this field
            if match_stage:
                match_kwargs['stage'] = match_stage
            
            # Add team/player IDs based on category type
            if category.is_doubles():
                match_kwargs['team1_id'] = participant1.id
                match_kwargs['team2_id'] = participant2.id
            else:
                match_kwargs['player1_id'] = participant1.id
                match_kwargs['player2_id'] = participant2.id
            
            match = Match(**match_kwargs)
            db.session.add(match)
            db.session.flush()
            
            # Link with quarterfinal matches
            rounds[3][i]['match'].next_match_id = match.id
            rounds[3][i+1]['match'].next_match_id = match.id
            
            # Simulate match score
            if category.is_doubles():
                simulate_doubles_match_score(match, participant1, participant2)
                # Add to semifinals round
                rounds[2].append({
                    'match': match,
                    'winner': participant1 if match.winning_team_id == participant1.id else participant2
                })
            else:
                simulate_singles_match_score(match, participant1, participant2)
                # Add to semifinals round
                rounds[2].append({
                    'match': match,
                    'winner': participant1 if match.winning_player_id == participant1.id else participant2
                })
    
    # Create final match
    if len(rounds[2]) >= 2:
        participant1 = rounds[2][0]['winner']
        participant2 = rounds[2][1]['winner']
        
        # Create match
        match_kwargs = {
            'category_id': category.id,
            'round': 1,  # Round 1 for final
            'match_order': 0,
            'completed': True,
            'court': "Center Court"
        }
        
        # Add stage if the match has this field
        if match_stage:
            match_kwargs['stage'] = match_stage
        
        # Add team/player IDs based on category type
        if category.is_doubles():
            match_kwargs['team1_id'] = participant1.id
            match_kwargs['team2_id'] = participant2.id
        else:
            match_kwargs['player1_id'] = participant1.id
            match_kwargs['player2_id'] = participant2.id
        
        match = Match(**match_kwargs)
        db.session.add(match)
        db.session.flush()
        
        # Link with semifinal matches
        rounds[2][0]['match'].next_match_id = match.id
        rounds[2][1]['match'].next_match_id = match.id
        
        # Simulate match score
        if category.is_doubles():
            simulate_doubles_match_score(match, participant1, participant2)
            # Add to finals round
            rounds[1].append({
                'match': match,
                'winner': participant1 if match.winning_team_id == participant1.id else participant2
            })
        else:
            simulate_singles_match_score(match, participant1, participant2)
            # Add to finals round
            rounds[1].append({
                'match': match,
                'winner': participant1 if match.winning_player_id == participant1.id else participant2
            })
    
    # Create 3rd place match if supported
    playoff_stage = MatchStage.PLAYOFF if 'MatchStage' in globals() else None
    if playoff_stage and len(rounds[2]) >= 2:
        # Get semifinal losers
        semifinal_losers = []
        for match_data in rounds[2]:
            match = match_data['match']
            if category.is_doubles():
                loser = match.team1 if match.losing_team_id == match.team1_id else match.team2
            else:
                loser = match.player1 if match.losing_player_id == match.player1_id else match.player2
            semifinal_losers.append(loser)
        
        if len(semifinal_losers) == 2:
            playoff_kwargs = {
                'category_id': category.id,
                'round': 1.5,  # Round 1.5 for 3rd place match
                'match_order': 0,
                'completed': True,
                'court': "Court 1",
                'stage': playoff_stage
            }
            
            # Add team/player IDs based on category type
            if category.is_doubles():
                playoff_kwargs['team1_id'] = semifinal_losers[0].id
                playoff_kwargs['team2_id'] = semifinal_losers[1].id
            else:
                playoff_kwargs['player1_id'] = semifinal_losers[0].id
                playoff_kwargs['player2_id'] = semifinal_losers[1].id
            
            playoff = Match(**playoff_kwargs)
            db.session.add(playoff)
            db.session.flush()
            
            # Simulate 3rd place match
            if category.is_doubles():
                simulate_doubles_match_score(playoff, semifinal_losers[0], semifinal_losers[1])
            else:
                simulate_singles_match_score(playoff, semifinal_losers[0], semifinal_losers[1])
    
    db.session.commit()

def simulate_doubles_match_score(match, team1, team2):
    """Simulate a doubles match score"""
    if not team1 or not team2:
        return
        
    # Calculate team strength based on players' points
    team1_player1 = PlayerProfile.query.get(team1.player1_id)
    team1_player2 = PlayerProfile.query.get(team1.player2_id)
    team2_player1 = PlayerProfile.query.get(team2.player1_id)
    team2_player2 = PlayerProfile.query.get(team2.player2_id)
    
    # Determine which points to use based on the category
    category = TournamentCategory.query.get(match.category_id)
    
    if category.category_type == CategoryType.MENS_DOUBLES:
        team1_strength = (getattr(team1_player1, 'mens_doubles_points', 1000) + 
                          getattr(team1_player2, 'mens_doubles_points', 1000)) / 2
        team2_strength = (getattr(team2_player1, 'mens_doubles_points', 1000) + 
                          getattr(team2_player2, 'mens_doubles_points', 1000)) / 2
    elif category.category_type == CategoryType.WOMENS_DOUBLES:
        team1_strength = (getattr(team1_player1, 'womens_doubles_points', 1000) + 
                          getattr(team1_player2, 'womens_doubles_points', 1000)) / 2
        team2_strength = (getattr(team2_player1, 'womens_doubles_points', 1000) + 
                          getattr(team2_player2, 'womens_doubles_points', 1000)) / 2
    elif category.category_type == CategoryType.MIXED_DOUBLES:
        team1_strength = (getattr(team1_player1, 'mixed_doubles_points', 1000) + 
                          getattr(team1_player2, 'mixed_doubles_points', 1000)) / 2
        team2_strength = (getattr(team2_player1, 'mixed_doubles_points', 1000) + 
                          getattr(team2_player2, 'mixed_doubles_points', 1000)) / 2
    else:
        team1_strength = 1000
        team2_strength = 1000
    
    # Add randomness
    team1_strength = max(500, min(2000, team1_strength * random.uniform(0.8, 1.2)))
    team2_strength = max(500, min(2000, team2_strength * random.uniform(0.8, 1.2)))
    
    # Determine how many sets (best of 3)
    team1_sets = 0
    team2_sets = 0
    
    # Play sets until someone wins
    for set_num in range(1, 4):
        if team1_sets == 2 or team2_sets == 2:
            break
            
        # Simulate set
        if random.random() < team1_strength / (team1_strength + team2_strength):
            # Team 1 wins set
            team1_score = 11
            team2_score = random.randint(0, 9)
            team1_sets += 1
        else:
            # Team 2 wins set
            team1_score = random.randint(0, 9)
            team2_score = 11
            team2_sets += 1
            
        # Create score record
        score = MatchScore(
            match_id=match.id,
            set_number=set_num,
            player1_score=team1_score,
            player2_score=team2_score
        )
        db.session.add(score)
    
    # Set match winner
    if team1_sets > team2_sets:
        match.winning_team_id = team1.id
        match.losing_team_id = team2.id
    else:
        match.winning_team_id = team2.id
        match.losing_team_id = team1.id
    
    # Add random third set if it went to 3
    if team1_sets + team2_sets == 3 and team1_sets != 3 and team2_sets != 3:
        extra_score = MatchScore(
            match_id=match.id,
            set_number=3,
            player1_score=15 if team1_sets > team2_sets else random.randint(0, 10),
            player2_score=random.randint(0, 10) if team1_sets > team2_sets else 15
        )
        db.session.add(extra_score)
    
    # Mark match as completed
    match.completed = True
    
    db.session.flush()

def simulate_singles_match_score(match, player1, player2):
    """Simulate a singles match score"""
    if not player1 or not player2:
        return
        
    # Calculate player strength based on points
    category = TournamentCategory.query.get(match.category_id)
    
    if category.category_type == CategoryType.MENS_SINGLES:
        player1_strength = getattr(player1, 'mens_singles_points', 1000)
        player2_strength = getattr(player2, 'mens_singles_points', 1000)
    elif category.category_type == CategoryType.WOMENS_SINGLES:
        player1_strength = getattr(player1, 'womens_singles_points', 1000)
        player2_strength = getattr(player2, 'womens_singles_points', 1000)
    else:
        player1_strength = 1000
        player2_strength = 1000
    
    # Add randomness
    player1_strength = max(500, min(2000, player1_strength * random.uniform(0.8, 1.2)))
    player2_strength = max(500, min(2000, player2_strength * random.uniform(0.8, 1.2)))
    
    # Determine how many sets (best of 3)
    player1_sets = 0
    player2_sets = 0
    
    # Play sets until someone wins
    for set_num in range(1, 4):
        if player1_sets == 2 or player2_sets == 2:
            break
            
        # Simulate set
        if random.random() < player1_strength / (player1_strength + player2_strength):
            # Player 1 wins set
            player1_score = 11
            player2_score = random.randint(0, 9)
            player1_sets += 1
        else:
            # Player 2 wins set
            player1_score = random.randint(0, 9)
            player2_score = 11
            player2_sets += 1
            
        # Create score record
        score = MatchScore(
            match_id=match.id,
            set_number=set_num,
            player1_score=player1_score,
            player2_score=player2_score
        )
        db.session.add(score)
    
    # Set match winner
    if player1_sets > player2_sets:
        match.winning_player_id = player1.id
        match.losing_player_id = player2.id
    else:
        match.winning_player_id = player2.id
        match.losing_player_id = player1.id
    
    # Add random third set if it went to 3
    if player1_sets + player2_sets == 3 and player1_sets != 3 and player2_sets != 3:
        extra_score = MatchScore(
            match_id=match.id,
            set_number=3,
            player1_score=15 if player1_sets > player2_sets else random.randint(0, 10),
            player2_score=random.randint(0, 10) if player1_sets > player2_sets else 15
        )
        db.session.add(extra_score)
    
    # Mark match as completed
    match.completed = True
    
    db.session.flush()

def create_upcoming_tournaments(organizer):
    """Create several upcoming tournaments for display on the homepage"""
    print("Creating upcoming tournaments...")
    
    # List of upcoming tournaments with realistic details
    upcoming_tournaments_data = [
        {
            "name": "Black Desert Resort Red Rock Open",
            "start_date": datetime.now() + timedelta(days=45),  # About 1.5 months away
            "end_date": datetime.now() + timedelta(days=49),
            "location": "St. George, Utah",
            "venue": "Black Desert Resort",
            "address": "1500 Desert Ridge Dr, Ivins, UT 84738",
            "description": "Join us for the premier southwestern desert pickleball event featuring stunning red rock views.",
            "logo": "https://www.ppatour.com/wp-content/uploads/2024/11/PPA-web-sizes-07.webp",
            "banner": "https://www.ppatour.com/wp-content/uploads/2023/11/2-Querrey-and-Walker-3.webp",
            "tier": TournamentTier.OPEN,
            "prize_pool": 120000.0
        },
        {
            "name": "Columbia Challenger",
            "start_date": datetime.now() + timedelta(days=18),  # About 3 weeks away
            "end_date": datetime.now() + timedelta(days=20),
            "location": "Columbia, South Carolina",
            "venue": "Columbia Tennis Center",
            "address": "31 Polo Rd, Columbia, SC 29223",
            "description": "A challenger series tournament showcasing rising talent in the southeast region.",
            "logo": "https://www.ppatour.com/wp-content/uploads/2024/11/PPA-web-sizes-07.webp",
            "banner": "https://www.ppatour.com/wp-content/uploads/2023/09/champ-saturday-scaled-1.webp",
            "tier": TournamentTier.CHALLENGE,
            "prize_pool": 75000.0
        },
        {
            "name": "Midwest Cup",
            "start_date": datetime.now() + timedelta(days=72),  # About 2.5 months away
            "end_date": datetime.now() + timedelta(days=76),
            "location": "Chicago, Illinois",
            "venue": "Chicago Indoor Sports Arena",
            "address": "155 W Harrison St, Chicago, IL 60605",
            "description": "The premier Midwest pickleball showcase featuring top talent from across the region.",
            "logo": "https://www.ppatour.com/wp-content/uploads/2024/11/PPA-web-sizes-07.webp",
            "banner": "https://www.ppatour.com/wp-content/uploads/2024/10/challengers_columbia.png",
            "tier": TournamentTier.CUP,
            "prize_pool": 100000.0
        }
    ]
    
    created_tournaments = []
    for tournament_data in upcoming_tournaments_data:
        # Check if tournament already exists
        tournament = Tournament.query.filter_by(name=tournament_data["name"]).first()
        if tournament:
            db.session.delete(tournament)
            db.session.commit()
        
        # Create new tournament
        tournament = Tournament(
            name=tournament_data["name"],
            organizer_id=organizer.id,
            location=tournament_data["location"],
            description=tournament_data["description"],
            start_date=tournament_data["start_date"],
            end_date=tournament_data["end_date"],
            registration_deadline=tournament_data["start_date"] - timedelta(days=7),
            tier=tournament_data["tier"],
            format=TournamentFormat.SINGLE_ELIMINATION,
            status=TournamentStatus.UPCOMING,
            prize_pool=tournament_data["prize_pool"],
            registration_fee=150.0,
            logo=tournament_data.get("logo"),
            banner=tournament_data.get("banner")
        )
        db.session.add(tournament)
        created_tournaments.append(tournament)
    
    db.session.commit()
    return created_tournaments

def create_platform_sponsors():
    """Create platform sponsors for display in the 'Featured Partners' section"""
    print("Creating platform sponsors...")
    
    # Clear existing sponsors
    existing_sponsors = PlatformSponsor.query.all()
    for sponsor in existing_sponsors:
        db.session.delete(sponsor)
    
    # Create new sponsors with realistic data
    sponsors_data = [
        {
            "name": "Carvana",
            "logo": "https://www.ppatour.com/wp-content/uploads/2024/10/Carvana-LOGO-Primary-Horizontal-Blue-RGB-1.png",
            "website": "https://www.carvana.com/",
            "is_featured": True,
            "tier": "Premier"
        },
        {
            "name": "Veolia",
            "logo": "https://www.ppatour.com/wp-content/uploads/2024/09/RGB_VEOLIA_HD.png",
            "website": "https://www.veolia.com/",
            "is_featured": True,
            "tier": "Premier"
        },
        {
            "name": "Humana",
            "logo": "https://www.ppatour.com/wp-content/uploads/2024/09/Hum_Logo_R_Green_4C-2-preferred-when-possible.png",
            "website": "https://www.humana.com/",
            "is_featured": True,
            "tier": "Premier"
        },
        {
            "name": "CIBC",
            "logo": "https://www.ppatour.com/wp-content/uploads/2023/06/cibc.png",
            "website": "https://www.cibc.com/",
            "is_featured": True,
            "tier": "Premier"
        }
    ]
    
    created_sponsors = []
    for sponsor_data in sponsors_data:
        sponsor = PlatformSponsor(
            name=sponsor_data["name"],
            logo=sponsor_data["logo"],
            website=sponsor_data["website"],
            is_featured=sponsor_data["is_featured"],
            tier=sponsor_data["tier"],
            description=f"Official {sponsor_data['tier']} Partner of the Pro Pickleball Tour"
        )
        db.session.add(sponsor)
        created_sponsors.append(sponsor)
    
    db.session.commit()
    return created_sponsors

def main():
    """Main function to seed the database"""
    # Reset database
    if len(sys.argv) > 1 and sys.argv[1] == '--reset':
        print("Dropping all tables...")
        db.drop_all()
        print("Creating all tables...")
        db.create_all()
    
    # Create admin and organizer
    admin, organizer = create_admin_and_organizer()
    
    # Create PPA players
    all_players = create_ppa_players()
    
    # Create Texas Open tournament (ongoing)
    texas_open, texas_categories = create_texas_open(organizer, all_players)

    # Create upcoming tournaments
    upcoming_tournaments = create_upcoming_tournaments(organizer)

    # Create Rocky Mountain Championship (completed)
    rocky_mountain, rocky_categories = create_completed_tournament(organizer, all_players)

    # Create platform sponsors
    platform_sponsors = create_platform_sponsors()
    
    print("Database seeded successfully!")
    print(f"Created Texas Open (ongoing) with {len(texas_categories)} categories")
    print(f"Created Rocky Mountain Championship (completed) with {len(rocky_categories)} categories")

if __name__ == '__main__':
    with app.app_context():
        main()