"""
Seed script for creating tournament registrations.
Creates teams and registrations for tournament categories.
"""

from app.models import Tournament, TournamentCategory, CategoryType, Registration, User, PlayerProfile, Team
from .seed_base import app, db, commit_changes, generate_reference, random_phone
from .seed_users import create_player
from datetime import datetime, timedelta
import random
import string
import sys

def register_team(category, player1, player2, seed=None, commit=True):
    """Register a team for a doubles category"""
    # Check if registration exists
    registration = Registration.query.filter_by(
        category_id=category.id,
        player_id=player1.player_profile.id,
        partner_id=player2.player_profile.id
    ).first()
    
    if registration:
        print(f"Registration for {player1.full_name}/{player2.full_name} in {category.name} already exists")
        return registration
    
    # Create tournament object if we only have the ID
    tournament = category.tournament
    
    # Create registration
    registration = Registration(
        category_id=category.id,
        registration_date=datetime.now() - timedelta(days=random.randint(5, 15)),
        registration_fee=category.registration_fee,
        
        # Flag this as a team registration
        is_team_registration=True,
        
        # Payment info
        payment_status='paid',
        payment_verified=True,
        payment_verified_at=datetime.now() - timedelta(days=random.randint(1, 5)),
        payment_proof=f"payment_{player1.id}_{player2.id}.png",
        payment_proof_uploaded_at=datetime.now() - timedelta(days=random.randint(3, 7)),
        payment_reference=generate_reference(tournament.payment_reference_prefix),
        is_approved=True,
        # Player 1 details
        player_id=player1.player_profile.id,
        player1_name=player1.full_name,
        player1_email=player1.email,
        player1_phone=player1.phone or random_phone(),
        player1_dupr_id=player1.player_profile.dupr_id or ''.join(random.choices(string.ascii_uppercase, k=2) + random.choices(string.digits, k=4)),
        player1_dupr_rating=player1.player_profile.mens_doubles_points/200 if category.category_type == CategoryType.MENS_DOUBLES else
                            player1.player_profile.womens_doubles_points/200 if category.category_type == CategoryType.WOMENS_DOUBLES else
                            player1.player_profile.mixed_doubles_points/200,
        player1_date_of_birth=datetime(
            random.randint(1980, 2000), 
            random.randint(1, 12), 
            random.randint(1, 28)
        ).date(),
        player1_nationality=player1.player_profile.country,
        
        # Player 2 details
        partner_id=player2.player_profile.id,
        player2_name=player2.full_name,
        player2_email=player2.email,
        player2_phone=player2.phone or random_phone(),
        player2_dupr_id=player2.player_profile.dupr_id or ''.join(random.choices(string.ascii_uppercase, k=2) + random.choices(string.digits, k=4)),
        player2_dupr_rating=player2.player_profile.mens_doubles_points/200 if category.category_type == CategoryType.MENS_DOUBLES else
                            player2.player_profile.womens_doubles_points/200 if category.category_type == CategoryType.WOMENS_DOUBLES else
                            player2.player_profile.mixed_doubles_points/200,
        player2_date_of_birth=datetime(
            random.randint(1980, 2000), 
            random.randint(1, 12), 
            random.randint(1, 28)
        ).date(),
        player2_nationality=player2.player_profile.country,
        
        # Team seed
        seed=seed,
        
        # Optional check-in status (50% checked in)
        checked_in=random.random() > 0.5,
        check_in_time=datetime.now() - timedelta(hours=random.randint(1, 5)) if random.random() > 0.5 else None,
        
        # Agreements
        terms_agreement=True,
        liability_waiver=True,
        media_release=True,
        pdpa_consent=True,
    )
    db.session.add(registration)
    
    if commit:
        commit_changes(f"Registration for {player1.full_name}/{player2.full_name} in {category.name} created")
    
    return registration

def create_team(category, player1, player2, commit=True):
    """Create a team for the tournament"""
    # Check if team exists
    team = Team.query.filter_by(
        category_id=category.id,
        player1_id=player1.player_profile.id,
        player2_id=player2.player_profile.id
    ).first()
    
    if team:
        print(f"Team {player1.full_name}/{player2.full_name} for {category.name} already exists")
        return team
    
    # Create team
    team = Team(
        player1_id=player1.player_profile.id,
        player2_id=player2.player_profile.id,
        category_id=category.id
    )
    db.session.add(team)
    
    if commit:
        commit_changes(f"Team {player1.full_name}/{player2.full_name} for {category.name} created")
    
    return team

def seed_mens_doubles_registrations(category_name="Men's Doubles Open", num_teams=16):
    """Create registrations for Men's Doubles category"""
    # Get tournament
    tournament = Tournament.query.filter_by(name="SportsSync-Oncourt Pickleball Tournament").first()
    if not tournament:
        print("Tournament not found. Please run seed_tournament.py first.")
        return []
    
    # Get category
    category = TournamentCategory.query.filter_by(
        tournament_id=tournament.id,
        name=category_name
    ).first()
    
    if not category:
        print(f"Category '{category_name}' not found.")
        return []
    
    # Generate player pairs for teams
    team_data = [
        # Team 1 (Seed 1)
        {"p1": "John Smith", "p2": "Michael Wong", "country": "Malaysia", "seed": 1, "dupr": 5.5},
        # Team 2 (Seed 2)
        {"p1": "David Lee", "p2": "Richard Tan", "country": "Singapore", "seed": 2, "dupr": 5.4},
        # Team 3 (Seed 3)
        {"p1": "Thomas Chen", "p2": "William Zhang", "country": "Taiwan", "seed": 3, "dupr": 5.3},
        # Team 4 (Seed 4)
        {"p1": "James Lim", "p2": "Robert Ng", "country": "Malaysia", "seed": 4, "dupr": 5.2},
        # Remaining teams with seeds or unseeded
        {"p1": "Daniel Chong", "p2": "Kevin Yap", "country": "Malaysia", "seed": 5, "dupr": 5.1},
        {"p1": "Joseph Tan", "p2": "Charles Kim", "country": "South Korea", "seed": 6, "dupr": 5.0},
        {"p1": "Edward Wu", "p2": "Steven Zhou", "country": "China", "seed": 7, "dupr": 4.9},
        {"p1": "Kenneth Park", "p2": "George Huang", "country": "Taiwan", "seed": 8, "dupr": 4.8},
        {"p1": "Ryan Tan", "p2": "Jason Lee", "country": "Malaysia", "seed": None, "dupr": 4.7},
        {"p1": "Peter Wang", "p2": "Eric Liu", "country": "China", "seed": None, "dupr": 4.6},
        {"p1": "Frank Kim", "p2": "Victor Kang", "country": "South Korea", "seed": None, "dupr": 4.5},
        {"p1": "Henry Lau", "p2": "Timothy Goh", "country": "Singapore", "seed": None, "dupr": 4.4},
        {"p1": "Alex Yeo", "p2": "Brian Tan", "country": "Malaysia", "seed": None, "dupr": 4.3},
        {"p1": "Oscar Chan", "p2": "Nathan Lim", "country": "Malaysia", "seed": None, "dupr": 4.2},
        {"p1": "Patrick Wong", "p2": "Quentin Cheung", "country": "Hong Kong", "seed": None, "dupr": 4.1},
        {"p1": "Samuel Chiu", "p2": "Umar Teo", "country": "Indonesia", "seed": None, "dupr": 4.0}
    ]
    
    # Limit to requested number of teams
    team_data = team_data[:num_teams]
    
    registrations = []
    teams = []
    
    # Register teams
    for team in team_data:
        # Get or create players
        p1 = User.query.filter_by(full_name=team["p1"]).first()
        if not p1:
            p1 = create_player(team["p1"], team["country"], team["dupr"], commit=False)
        
        p2 = User.query.filter_by(full_name=team["p2"]).first()
        if not p2:
            p2 = create_player(team["p2"], team["country"], team["dupr"], commit=False)
        
        # Create registration and team
        registration = register_team(category, p1, p2, team["seed"], commit=False)
        registrations.append(registration)
        
        team_obj = create_team(category, p1, p2, commit=False)
        teams.append(team_obj)
    
    # Commit all changes
    commit_changes(f"Created {len(teams)} teams and registrations for {category_name}")
    
    return teams

def seed_womens_doubles_registrations(category_name="Women's Doubles Open", num_teams=16):
    """Create registrations for Women's Doubles category"""
    # Get tournament
    tournament = Tournament.query.filter_by(name="SportsSync-Oncourt Pickleball Tournament").first()
    if not tournament:
        print("Tournament not found. Please run seed_tournament.py first.")
        return []
    
    # Get category
    category = TournamentCategory.query.filter_by(
        tournament_id=tournament.id,
        name=category_name
    ).first()
    
    if not category:
        print(f"Category '{category_name}' not found.")
        return []
    
    # Generate player pairs for teams
    team_data = [
        # Team 1 (Seed 1)
        {"p1": "Alice Johnson", "p2": "Emma Davis", "country": "USA", "seed": 1, "dupr": 5.3},
        # Team 2 (Seed 2)
        {"p1": "Sophia Chen", "p2": "Olivia Wang", "country": "Taiwan", "seed": 2, "dupr": 5.2},
        # Team 3 (Seed 3)
        {"p1": "Isabella Kim", "p2": "Mia Park", "country": "South Korea", "seed": 3, "dupr": 5.1},
        # Team 4 (Seed 4)
        {"p1": "Amelia Tan", "p2": "Charlotte Ng", "country": "Malaysia", "seed": 4, "dupr": 5.0},
        # Remaining teams with seeds or unseeded
        {"p1": "Harper Lee", "p2": "Abigail Lim", "country": "Singapore", "seed": 5, "dupr": 4.9},
        {"p1": "Emily Zhang", "p2": "Elizabeth Wu", "country": "China", "seed": 6, "dupr": 4.8},
        {"p1": "Avery Wong", "p2": "Sofia Cheung", "country": "Hong Kong", "seed": 7, "dupr": 4.7},
        {"p1": "Scarlett Yeo", "p2": "Victoria Lin", "country": "Malaysia", "seed": 8, "dupr": 4.6},
        {"p1": "Grace Lai", "p2": "Chloe Hsu", "country": "Taiwan", "seed": None, "dupr": 4.5},
        {"p1": "Lily Yuan", "p2": "Hannah Zhao", "country": "China", "seed": None, "dupr": 4.4},
        {"p1": "Zoe Kang", "p2": "Madison Ahn", "country": "South Korea", "seed": None, "dupr": 4.3},
        {"p1": "Layla Teo", "p2": "Penelope Goh", "country": "Singapore", "seed": None, "dupr": 4.2},
        {"p1": "Nora Abdullah", "p2": "Riley Hashim", "country": "Malaysia", "seed": None, "dupr": 4.1},
        {"p1": "Stella Liew", "p2": "Luna Chang", "country": "Taiwan", "seed": None, "dupr": 4.0},
        {"p1": "Hazel Fong", "p2": "Violet Teoh", "country": "Malaysia", "seed": None, "dupr": 3.9},
        {"p1": "Lucy Kwok", "p2": "Audrey Chia", "country": "Singapore", "seed": None, "dupr": 3.8}
    ]
    
    # Limit to requested number of teams
    team_data = team_data[:num_teams]
    
    registrations = []
    teams = []
    
    # Register teams
    for team in team_data:
        # Get or create players
        p1 = User.query.filter_by(full_name=team["p1"]).first()
        if not p1:
            p1 = create_player(team["p1"], team["country"], team["dupr"], commit=False)
        
        p2 = User.query.filter_by(full_name=team["p2"]).first()
        if not p2:
            p2 = create_player(team["p2"], team["country"], team["dupr"], commit=False)
        
        # Create registration and team
        registration = register_team(category, p1, p2, team["seed"], commit=False)
        registrations.append(registration)
        
        team_obj = create_team(category, p1, p2, commit=False)
        teams.append(team_obj)
    
    # Commit all changes
    commit_changes(f"Created {len(teams)} teams and registrations for {category_name}")
    
    return teams

def main():
    """Run when this script is executed directly"""
    # Seed men's doubles registrations
    mens_teams = seed_mens_doubles_registrations()
    print(f"Created {len(mens_teams)} men's doubles teams")
    
    # Seed women's doubles registrations
    womens_teams = seed_womens_doubles_registrations()
    print(f"Created {len(womens_teams)} women's doubles teams")

if __name__ == "__main__":
    with app.app_context():
        main()
