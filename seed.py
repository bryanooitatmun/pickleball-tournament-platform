"""
Seed script for creating a complete tournament with group stage and knockout phase
for Men's Doubles category
"""
import os
import sys
from datetime import datetime, timedelta
import random
from flask import Flask
from app import create_app, db
from app.models import (User, UserRole, Tournament, TournamentCategory, 
                       TournamentTier, TournamentFormat, TournamentStatus, 
                       CategoryType, PlayerProfile, Registration, Match,
                       MatchScore, Team)

# Create app context
app = create_app()
app.app_context().push()

def create_users_and_players():
    """Create admin, organizer and player users"""
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
    
    # Create 16 male players with profiles
    players = []
    player_data = [
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
    ]
    
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
            
            # Create player profile
            profile = PlayerProfile(
                user_id=user.id,
                full_name=data['name'],
                country=data['country'],
                city=random.choice(['New York', 'London', 'Paris', 'Tokyo', 'Sydney', 'Madrid', 'Toronto']),
                age=random.randint(18, 40),
                plays=data['plays'],
                height=f"{random.randint(5, 6)}'{random.randint(0, 11)}\"",
                paddle="Pro Strike 2000",
                mens_doubles_points=random.randint(500, 2000),
                turned_pro=random.randint(2015, 2023)
            )
            db.session.add(profile)
        else:
            profile = PlayerProfile.query.filter_by(user_id=user.id).first()
            if not profile.mens_doubles_points:
                profile.mens_doubles_points = random.randint(500, 2000)
        
        players.append(profile)
    
    db.session.commit()
    return admin, organizer, players

def form_doubles_teams(players):
    """Form 8 doubles teams from 16 players"""
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
                players.remove(regional_players[i])
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

def create_tournament(organizer, teams):
    """Create a tournament with group stage and knockout phase for doubles"""
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
        description='A premier pickleball doubles tournament featuring group stage and knockout phases.',
        start_date=start_date,
        end_date=end_date,
        registration_deadline=registration_deadline,
        tier=TournamentTier.OPEN,
        format=TournamentFormat.GROUP_KNOCKOUT,
        status=TournamentStatus.COMPLETED,  # Set as completed for this example
        prize_pool=10000.0,
        registration_fee=150.0
    )
    db.session.add(tournament)
    db.session.flush()
    
    # Create men's doubles category
    mens_doubles = TournamentCategory(
        tournament_id=tournament.id,
        category_type=CategoryType.MENS_DOUBLES,
        max_participants=16,
        points_awarded=1400
    )
    db.session.add(mens_doubles)
    db.session.flush()
    
    # Create and register teams
    team_objects = []
    for team in teams:
        player1, player2 = team['players']
        
        # Create team object
        team_obj = Team(
            player1_id=player1.id,
            player2_id=player2.id,
            category_id=mens_doubles.id
        )
        db.session.add(team_obj)
        db.session.flush()
        team_objects.append(team_obj)
        
        # Register both players
        reg1 = Registration(
            player_id=player1.id,
            category_id=mens_doubles.id,
            partner_id=player2.id,
            is_approved=True,
            payment_status='paid',
            payment_date=datetime.now() - timedelta(days=14)
        )
        db.session.add(reg1)
        
        reg2 = Registration(
            player_id=player2.id,
            category_id=mens_doubles.id,
            partner_id=player1.id,
            is_approved=True,
            payment_status='paid',
            payment_date=datetime.now() - timedelta(days=14)
        )
        db.session.add(reg2)
    
    db.session.commit()
    
    # Set up groups (4 groups of 2 teams)
    random.shuffle(team_objects)
    
    groups = [
        {'name': 'Group A', 'teams': team_objects[0:2]},
        {'name': 'Group B', 'teams': team_objects[2:4]},
        {'name': 'Group C', 'teams': team_objects[4:6]},
        {'name': 'Group D', 'teams': team_objects[6:8]},
    ]
    
    # Create group stage matches
    print("Creating group stage matches...")
    create_group_stage_matches(tournament, mens_doubles, groups)
    
    # Create knockout stage
    print("Creating knockout stage matches...")
    create_knockout_stage(tournament, mens_doubles, groups)
    
    return tournament

def create_group_stage_matches(tournament, category, groups):
    """Create and simulate group stage matches for doubles"""
    round_number = 4  # Use round 4 for group stage
    match_order = 0
    
    for group_idx, group in enumerate(groups):
        teams = group['teams']
        
        # Create matches between teams in the group
        for i in range(len(teams)):
            for j in range(i + 1, len(teams)):
                team1 = teams[i]
                team2 = teams[j]
                
                # Create match
                match = Match(
                    category_id=category.id,
                    round=round_number,
                    match_order=match_order,
                    team1_id=team1.id,
                    team2_id=team2.id,
                    completed=True,
                    court=f"Court {random.randint(1, 8)}"
                )
                db.session.add(match)
                db.session.flush()
                
                # Simulate match score
                simulate_doubles_match_score(match, team1, team2)
                match_order += 1

    db.session.commit()
    
    # Calculate group standings and determine who advances
    for group in groups:
        standings = calculate_doubles_group_standings(group['teams'], category)
        # Top team advances from each group
        group['advancing'] = standings[:1]

def calculate_doubles_group_standings(teams, category):
    """Calculate group standings for doubles teams"""
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
        
        # Process matches where team was team1
        for match in matches_team1:
            if match.winning_team_id == team.id:
                wins += 1
            
            # Count sets
            for score in match.scores:
                if score.player1_score > score.player2_score:
                    sets_won += 1
                else:
                    sets_lost += 1
        
        # Process matches where team was team2
        for match in matches_team2:
            if match.winning_team_id == team.id:
                wins += 1
            
            # Count sets
            for score in match.scores:
                if score.player2_score > score.player1_score:
                    sets_won += 1
                else:
                    sets_lost += 1
        
        # Calculate set differential
        set_diff = sets_won - sets_lost
        
        standings.append({
            'team': team,
            'wins': wins,
            'matches': total_matches,
            'sets_won': sets_won,
            'sets_lost': sets_lost,
            'set_diff': set_diff
        })
    
    # Sort by wins, then set differential
    standings.sort(key=lambda x: (x['wins'], x['set_diff']), reverse=True)
    
    return [s['team'] for s in standings]

def create_knockout_stage(tournament, category, groups):
    """Create and simulate knockout stage matches for doubles"""
    # Set up semifinals - Group winners play each other
    semifinal_matches = [
        (groups[0]['advancing'][0], groups[1]['advancing'][0]),  # A1 vs B1
        (groups[2]['advancing'][0], groups[3]['advancing'][0]),  # C1 vs D1
    ]
    
    # Create semifinal matches
    semifinal_winners = []
    for i, (team1, team2) in enumerate(semifinal_matches):
        match = Match(
            category_id=category.id,
            round=2,  # Round 2 for semifinals
            match_order=i,
            team1_id=team1.id,
            team2_id=team2.id,
            completed=True,
            court="Center Court"
        )
        db.session.add(match)
        db.session.flush()
        
        # Simulate match
        simulate_doubles_match_score(match, team1, team2)
        
        # Determine winner
        winner = team1 if match.winning_team_id == team1.id else team2
        semifinal_winners.append(winner)
    
    # Create final match
    final = Match(
        category_id=category.id,
        round=1,  # Round 1 for final
        match_order=0,
        team1_id=semifinal_winners[0].id,
        team2_id=semifinal_winners[1].id,
        completed=True,
        court="Center Court"
    )
    db.session.add(final)
    db.session.flush()
    
    # Simulate final
    simulate_doubles_match_score(final, semifinal_winners[0], semifinal_winners[1])
    
    db.session.commit()

def simulate_doubles_match_score(match, team1, team2):
    """Simulate a doubles match score"""
    # Calculate team strength based on players' points
    team1_player1 = PlayerProfile.query.get(team1.player1_id)
    team1_player2 = PlayerProfile.query.get(team1.player2_id)
    team2_player1 = PlayerProfile.query.get(team2.player1_id)
    team2_player2 = PlayerProfile.query.get(team2.player2_id)
    
    team1_strength = (team1_player1.mens_doubles_points + team1_player2.mens_doubles_points) / 2
    team2_strength = (team2_player1.mens_doubles_points + team2_player2.mens_doubles_points) / 2
    
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

def main():
    """Main function to seed the database"""
    # Reset database
    if len(sys.argv) > 1 and sys.argv[1] == '--reset':
        print("Dropping all tables...")
        db.drop_all()
        print("Creating all tables...")
        db.create_all()
    
    # Create users and players
    admin, organizer, players = create_users_and_players()
    
    # Form doubles teams
    teams = form_doubles_teams(players)
    
    # Create tournament with group stage and knockout phase
    tournament = create_tournament(organizer, teams)
    
    print("Database seeded successfully!")

if __name__ == '__main__':
    with app.app_context():
        main()