"""
Enhanced seed script for testing multiple tournament formats, 
prize distribution, and group stage functionality
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
    MatchScore, Team, Group, GroupStanding, MatchStage
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

def create_users_and_players():
    """Create admin, organizer and players (both male and female)"""
    print("Creating users...")
    
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
    
    # Create male player data
    male_player_data = [
        {'name': 'Alex Williams', 'country': 'United States', 'plays': 'Right-handed'},
        {'name': 'John Smith', 'country': 'Canada', 'plays': 'Right-handed'},
        {'name': 'Carlos Brown', 'country': 'Brazil', 'plays': 'Right-handed'},
        {'name': 'David Martinez', 'country': 'Argentina', 'plays': 'Left-handed'},
        {'name': 'James Thompson', 'country': 'United States', 'plays': 'Right-handed'},
        {'name': 'Lucas Garcia', 'country': 'Spain', 'plays': 'Left-handed'},
        {'name': 'Liam Chen', 'country': 'China', 'plays': 'Right-handed'},
        {'name': 'Noah Yamamoto', 'country': 'Japan', 'plays': 'Right-handed'},
        {'name': 'Michael Lee', 'country': 'South Korea', 'plays': 'Right-handed'},
        {'name': 'Daniel Johnson', 'country': 'United Kingdom', 'plays': 'Right-handed'},
        {'name': 'Samuel Wilson', 'country': 'Australia', 'plays': 'Left-handed'},
        {'name': 'William Davis', 'country': 'Canada', 'plays': 'Right-handed'},
        {'name': 'Thomas White', 'country': 'New Zealand', 'plays': 'Right-handed'},
        {'name': 'George Brown', 'country': 'United States', 'plays': 'Right-handed'},
        {'name': 'Joseph Miller', 'country': 'United Kingdom', 'plays': 'Left-handed'},
        {'name': 'Henry Taylor', 'country': 'Australia', 'plays': 'Right-handed'},
        {'name': 'Alex Taylor', 'country': 'United States', 'plays': 'Right-handed'},
        {'name': 'John Miller', 'country': 'Canada', 'plays': 'Right-handed'},
        {'name': 'Carlos White', 'country': 'Brazil', 'plays': 'Right-handed'},
        {'name': 'David Brown', 'country': 'Argentina', 'plays': 'Left-handed'},
        {'name': 'James Davis', 'country': 'United States', 'plays': 'Right-handed'},
        {'name': 'Lucas Wilson', 'country': 'Spain', 'plays': 'Left-handed'},
        {'name': 'Liam Johnson', 'country': 'China', 'plays': 'Right-handed'},
        {'name': 'Noah Lee', 'country': 'Japan', 'plays': 'Right-handed'},
        {'name': 'Michael Yamamoto', 'country': 'South Korea', 'plays': 'Right-handed'},
        {'name': 'Daniel Chen', 'country': 'United Kingdom', 'plays': 'Right-handed'},
        {'name': 'Samuel Garcia', 'country': 'Australia', 'plays': 'Left-handed'},
        {'name': 'William Thompson', 'country': 'Canada', 'plays': 'Right-handed'},
        {'name': 'Thomas Martinez', 'country': 'New Zealand', 'plays': 'Right-handed'},
        {'name': 'George Smith', 'country': 'United States', 'plays': 'Right-handed'},
        {'name': 'Joseph Williams', 'country': 'United Kingdom', 'plays': 'Left-handed'},
        {'name': 'Henry Smith', 'country': 'Australia', 'plays': 'Right-handed'},
    ]
    
    # Create female player data
    female_player_data = [
        {'name': 'Emma Johnson', 'country': 'United States', 'plays': 'Right-handed'},
        {'name': 'Olivia Williams', 'country': 'Canada', 'plays': 'Right-handed'},
        {'name': 'Ava Martinez', 'country': 'Spain', 'plays': 'Right-handed'},
        {'name': 'Sophia Rodriguez', 'country': 'Argentina', 'plays': 'Left-handed'},
        {'name': 'Isabella Thompson', 'country': 'United States', 'plays': 'Right-handed'},
        {'name': 'Mia Garcia', 'country': 'Spain', 'plays': 'Left-handed'},
        {'name': 'Charlotte Kim', 'country': 'South Korea', 'plays': 'Right-handed'},
        {'name': 'Amelia Tanaka', 'country': 'Japan', 'plays': 'Right-handed'},
        {'name': 'Harper Wong', 'country': 'China', 'plays': 'Right-handed'},
        {'name': 'Evelyn Smith', 'country': 'United Kingdom', 'plays': 'Right-handed'},
        {'name': 'Abigail Wilson', 'country': 'Australia', 'plays': 'Left-handed'},
        {'name': 'Emily Davis', 'country': 'Canada', 'plays': 'Right-handed'},
        {'name': 'Ella White', 'country': 'New Zealand', 'plays': 'Right-handed'},
        {'name': 'Scarlett Brown', 'country': 'United States', 'plays': 'Right-handed'},
        {'name': 'Grace Miller', 'country': 'United Kingdom', 'plays': 'Left-handed'},
        {'name': 'Chloe Taylor', 'country': 'Australia', 'plays': 'Right-handed'},
    ]
    
    # Create players
    male_players = create_players(male_player_data, 'male')
    female_players = create_players(female_player_data, 'female')
    
    db.session.commit()
    return admin, organizer, {'male': male_players, 'female': female_players}

def create_players(player_data, gender):
    """Create player profiles with appropriate ratings"""
    players = []
    
    for i, data in enumerate(player_data):
        email = f"{data['name'].lower().replace(' ', '.')}@example.com"
        user = User.query.filter_by(email=email).first()
        
        if not user:
            user = User(
                username=data['name'].lower().replace(' ', '.'),
                email=email,
                role=UserRole.PLAYER
            )
            user.set_password('password')
            db.session.add(user)
            db.session.flush()  # Ensure user has an ID
            
            # Create player profile with appropriate ratings
            profile = PlayerProfile(
                user_id=user.id,
                full_name=data['name'],
                country=data['country'],
                city=random.choice(['New York', 'London', 'Paris', 'Tokyo', 'Sydney', 'Madrid', 'Toronto']),
                age=random.randint(18, 40),
                plays=data['plays'],
                height=f"{random.randint(5, 6)}'{random.randint(0, 11)}\"",
                paddle="Pro Strike 2000",
                turned_pro=random.randint(2015, 2023)
            )
            
            # Add gender-specific points and DUPR ratings
            if gender == 'male':
                profile.mens_singles_points = random.randint(500, 2000)
                profile.mens_doubles_points = random.randint(500, 2000)
                profile.mixed_doubles_points = random.randint(500, 2000)
                
                # Add DUPR ratings if the field exists
                if hasattr(profile, 'mens_singles_dupr'):
                    profile.mens_singles_dupr = round(random.uniform(3.5, 6.0), 1)
                    profile.mens_doubles_dupr = round(random.uniform(3.5, 6.0), 1)
                    profile.mixed_doubles_dupr = round(random.uniform(3.5, 6.0), 1)
            else:
                profile.womens_singles_points = random.randint(500, 2000)
                profile.womens_doubles_points = random.randint(500, 2000)
                profile.mixed_doubles_points = random.randint(500, 2000)
                
                # Add DUPR ratings if the field exists
                if hasattr(profile, 'womens_singles_dupr'):
                    profile.womens_singles_dupr = round(random.uniform(3.5, 6.0), 1)
                    profile.womens_doubles_dupr = round(random.uniform(3.5, 6.0), 1)
                    profile.mixed_doubles_dupr = round(random.uniform(3.5, 6.0), 1)
            
            db.session.add(profile)
        else:
            profile = PlayerProfile.query.filter_by(user_id=user.id).first()
            
            # Update points if needed
            if gender == 'male' and not profile.mens_doubles_points:
                profile.mens_singles_points = random.randint(500, 2000)
                profile.mens_doubles_points = random.randint(500, 2000)
                profile.mixed_doubles_points = random.randint(500, 2000)
            elif gender == 'female' and not profile.womens_doubles_points:
                profile.womens_singles_points = random.randint(500, 2000)
                profile.womens_doubles_points = random.randint(500, 2000)
                profile.mixed_doubles_points = random.randint(500, 2000)
        
        players.append(profile)
    
    return players

def form_doubles_teams(players, gender='male'):
    """Form doubles teams from players"""
    random.shuffle(players)
    teams = []
    
    # Form teams based on geographic proximity for more realism
    # Group players by continent/region
    regions = {
        "North America": ["United States", "Canada"],
        "South America": ["Brazil", "Argentina"],
        "Europe": ["United Kingdom", "Spain"],
        "Asia": ["China", "Japan", "South Korea"],
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

def create_tournament(organizer, all_players):
    """Create a comprehensive test tournament with multiple categories and formats"""
    print("Creating tournament...")
    
    # Create tournament
    tournament = Tournament.query.filter_by(name='Rocky Mountain Championship').first()
    if tournament:
        # If tournament already exists, delete it and recreate
        db.session.delete(tournament)
        db.session.commit()
    
    start_date = datetime.now() + timedelta(days=30)
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
    placings_calculated = False
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
                        placings_calculated = True
                        category_data['placings'] = placings
                except Exception as e:
                    print(f"Error calculating placings for {category_key}: {str(e)}")
        except Exception as e:
            print(f"Error distributing prize money: {str(e)}")
    
    # If service layer didn't work, calculate placings manually

    # if not placings_calculated:
    #     print("Service layer didn't calculate placings, using manual calculation...")
    #     categories = calculate_placings_manually(categories)
    
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

def register_players_and_create_teams(categories, all_players):
    """Register players to categories and create teams"""
    # Men's Doubles - Form teams and register 16 teams
    mens_doubles_teams = form_doubles_teams(all_players['male'][:32])

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
    mixed_teams = []
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
    for i, player in enumerate(all_players['male'][8:16]):
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
    # Set up groups
    random.shuffle(teams)
    
    # Create 4 groups with teams
    group_count = getattr(category, 'group_count', 4)
    teams_per_group = getattr(category, 'teams_per_group', 4)
    
    groups = []
    for i in range(group_count):
        start_idx = i * teams_per_group
        end_idx = start_idx + teams_per_group
        group_teams = teams[start_idx:end_idx]
        
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
    # Get MatchStage enum if it exists
    match_stage = MatchStage.KNOCKOUT if 'MatchStage' in globals() else None
    
    # Extract advancing teams from each group (top 2 from each group)
    # Format: [A1, A2, B1, B2, C1, C2, D1, D2]
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
        (advancing_teams[0], advancing_teams[7]),  # A1 vs D2
        (advancing_teams[2], advancing_teams[5]),  # B1 vs C2
        (advancing_teams[4], advancing_teams[3]),  # C1 vs B2
        (advancing_teams[6], advancing_teams[1]),  # D1 vs A2
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
        participant1 = participants[i]
        participant2 = participants[i+1] if i+1 < len(participants) else None
        
        if participant1 and participant2:
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

def main():
    """Main function to seed the database"""
    # Reset database
    if len(sys.argv) > 1 and sys.argv[1] == '--reset':
        print("Dropping all tables...")
        db.drop_all()
        print("Creating all tables...")
        db.create_all()
    
    # Create users and players
    admin, organizer, all_players = create_users_and_players()
    
    # Create tournament with various categories and formats
    tournament, categories = create_tournament(organizer, all_players)
    
    print("Database seeded successfully!")

if __name__ == '__main__':
    with app.app_context():
        main()