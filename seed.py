from app import create_app, db
from app.models import (
    User, UserRole, PlayerProfile, Tournament, TournamentCategory, 
    Match, MatchScore, Registration, Equipment, Sponsor,
    TournamentTier, TournamentFormat, TournamentStatus, CategoryType
)
from datetime import datetime, timedelta
import random

app = create_app()

def seed_users():
    # Create admin user
    admin = User(
        username='admin',
        email='admin@example.com',
        role=UserRole.ADMIN,
        is_active=True
    )
    admin.set_password('password')
    
    # Create an organizer
    organizer = User(
        username='organizer',
        email='organizer@example.com',
        role=UserRole.ORGANIZER,
        is_active=True
    )
    organizer.set_password('password')
    
    # Create some players
    players = []
    for i in range(1, 31):
        player = User(
            username=f'player{i}',
            email=f'player{i}@example.com',
            role=UserRole.PLAYER,
            is_active=True
        )
        player.set_password('password')
        players.append(player)
    
    # Add all users to the session
    db.session.add(admin)
    db.session.add(organizer)
    for player in players:
        db.session.add(player)
    
    db.session.commit()
    
    return admin, organizer, players

# Additional functions will be added in subsequent commits

def seed_database():
    with app.app_context():
        # Drop all tables and recreate them
        db.drop_all()
        db.create_all()
        
        # Seed users
        admin, organizer, players = seed_users()
        
        # More seeding will be added in subsequent functions
        
        print("Database seeded successfully!")

if __name__ == '__main__':
    seed_database()
