"""
Seed script for creating users with different roles.
Creates admin, organizer, referee, and player accounts with profiles.
"""

from app.models import User, UserRole, PlayerProfile
from .seed_base import app, db, commit_changes, random_phone, date_in_range
from werkzeug.security import generate_password_hash
import random
import string
from datetime import date, datetime, timedelta
import sys

def create_admin(username="admin", email="admin@example.com", password="sportssynccomplicatedpassword", commit=True):
    """Create an admin user account"""
    # Check if admin exists
    admin = User.query.filter_by(email=email).first()
    if admin:
        print(f"Admin user {email} already exists")
        return admin
    
    admin = User(
        username=username,
        email=email,
        full_name="Admin User",
        role=UserRole.ADMIN,
        is_active=True
    )
    admin.set_password(password)
    db.session.add(admin)
    
    if commit:
        commit_changes(f"Admin user {email} created")
    
    return admin

def create_organizer(username="organizer", email="organizer@example.com", password="sportssynccomplicatedpassword", commit=True):
    """Create an organizer user account"""
    # Check if organizer exists
    organizer = User.query.filter_by(email=email).first()
    if organizer:
        print(f"Organizer user {email} already exists")
        return organizer
    
    organizer = User(
        username=username,
        email=email,
        full_name="Tournament Organizer",
        role=UserRole.ORGANIZER,
        is_active=True
    )
    organizer.set_password(password)
    db.session.add(organizer)
    
    if commit:
        commit_changes(f"Organizer user {email} created")
    
    return organizer

def create_referee(username="referee", email="referee@example.com", password="sportssynccomplicatedpassword", commit=True):
    """Create a referee user account"""
    # Check if referee exists
    referee = User.query.filter_by(email=email).first()
    if referee:
        print(f"Referee user {email} already exists")
        return referee
    
    referee = User(
        username=username,
        email=email,
        full_name="Match Referee",
        role=UserRole.REFEREE,
        is_active=True
    )
    referee.set_password(password)
    db.session.add(referee)
    
    if commit:
        commit_changes(f"Referee user {email} created")
    
    return referee

def create_player(name, country="Malaysia", dupr_rating=None, email=None, username=None, password="password", commit=True):
    """Create a player user with profile"""
    if not username:
        username = name.lower().replace(" ", ".")
    
    if not email:
        email = f"{username}@example.com"
    
    # Check if player exists
    user = User.query.filter_by(email=email).first()
    if user:
        print(f"Player user {email} already exists")
        return user
    
    # Create the user account
    user = User(
        username=username,
        email=email,
        full_name=name,
        ic_number=''.join(random.choices(string.digits, k=12)),
        phone=random_phone(),
        role=UserRole.PLAYER,
        is_active=True
    )
    user.set_password(password)
    db.session.add(user)
    db.session.flush()  # Get user ID without committing
    
    # Create player profile
    profile = PlayerProfile(
        user_id=user.id,
        full_name=name,
        country=country,
        city=random.choice(["Kuala Lumpur", "Penang", "Johor Bahru", "Ipoh", "Melaka"]) if country == "Malaysia" else "Unknown",
        age=random.randint(18, 45),
        bio=f"Professional pickleball player from {country}.",
        plays=random.choice(["Right-handed", "Left-handed"]),
        height=f"{5 + random.randint(0, 10) // 12}'{random.randint(0, 11)}\"",
        paddle=random.choice([
            "Selkirk Vanguard Power Air",
            "Joola Hyperion CFS",
            "Paddletek Tempest Wave II",
            "Engage Pursuit MX",
            "ProKennex Pro Flight"
        ]),
        # Social media links
        instagram=f"https://instagram.com/{username}",
        facebook=f"https://facebook.com/{username}",
        twitter=f"https://twitter.com/{username}",
        tiktok=f"https://tiktok.com/@{username}",
        xiaohongshu=f"https://xiaohongshu.com/{username}",
        # Coach affiliation
        coach_academy=random.choice([
            "Elite Pickleball Academy",
            "Power Pickleball Training",
            "Premier Paddle Club",
            "Victory Pickleball School",
            None
        ]),
        # Player stats
        dupr_id=''.join(random.choices(string.ascii_uppercase, k=2) + random.choices(string.digits, k=4)),
        matches_won=random.randint(5, 50),
        matches_lost=random.randint(2, 20),
        avg_match_duration=random.randint(25, 60),
        
        # Ranking points
        mens_singles_points=random.randint(0, 1000) if "male_names" else 0,
        womens_singles_points=random.randint(0, 1000) if "female_names" else 0,
        mens_doubles_points=random.randint(0, 1200) if "male_names" else 0,
        womens_doubles_points=random.randint(0, 1200) if "female_names" else 0,
        mixed_doubles_points=random.randint(0, 1100),
        
        # Pro details
        turned_pro=random.randint(2018, 2023)
    )
    db.session.add(profile)
    
    if commit:
        commit_changes(f"Player user {email} with profile created")
    
    return user

def seed_users(num_players=32, num_referees=4):
    """Seed database with various user roles and accounts"""
    # Create admin
    create_admin(commit=False)
    
    # Create organizer
    create_organizer(commit=False)
    
    # Create referees
    for i in range(num_referees):
        create_referee(
            username=f"referee{i+1}",
            email=f"referee{i+1}@example.com",
            commit=False
        )
    
    # Create 16 male players
    male_names = [
        "John Smith", "Michael Wong", "David Lee", "Richard Tan", "Thomas Chen", 
        "William Zhang", "James Lim", "Robert Ng", "Daniel Chong", "Kevin Yap", 
        "Joseph Tan", "Charles Kim", "Edward Wu", "Steven Zhou", "Kenneth Park", "George Huang"
    ]
    
    # Create 16 female players
    female_names = [
        "Alice Johnson", "Emma Davis", "Sophia Chen", "Olivia Wang", "Isabella Kim",
        "Mia Park", "Amelia Tan", "Charlotte Ng", "Harper Lee", "Abigail Lim",
        "Emily Zhang", "Elizabeth Wu", "Avery Wong", "Sofia Cheung", "Scarlett Yeo", "Victoria Lin"
    ]
    
    # Create players
    for name in male_names + female_names:
        dupr_rating = round(random.uniform(3.5, 5.5), 1)
        country = random.choice(["Malaysia", "Singapore", "Thailand", "Indonesia", "Philippines", "Vietnam", "China", "Taiwan", "South Korea", "Japan"])
        create_player(name, country, dupr_rating, commit=False)
    
    # Commit all changes at once
    commit_changes("All users created successfully")
    
    # Return counts for reporting
    return {
        "admin": 1,
        "organizer": 1,
        "referees": num_referees,
        "players": len(male_names) + len(female_names)
    }

def main():
    """Run when this script is executed directly"""
    user_counts = seed_users()
    print(f"Created {user_counts['admin']} admin user")
    print(f"Created {user_counts['organizer']} organizer user")
    print(f"Created {user_counts['referees']} referee users")
    print(f"Created {user_counts['players']} player users with profiles")

if __name__ == "__main__":
    with app.app_context():
        main()
