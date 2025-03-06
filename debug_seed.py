"""
Debug script to check database content after seeding.
Run this with "python debug_seed.py" to see what's in your database.
"""

import os
import sys
from flask import Flask
from app import create_app, db
from app.models import User, UserRole, PlayerProfile, Tournament, TournamentCategory, Registration, TournamentStatus, CategoryType

def check_database():
    print("\n" + "="*80)
    print("CHECKING DATABASE CONTENTS")
    print("="*80)
    
    # Check users
    users = User.query.all()
    print(f"\nUSERS: {len(users)} total")
    for role in UserRole:
        count = User.query.filter_by(role=role).count()
        print(f"  - {role.name}: {count}")
    
    # Check player profiles
    profiles = PlayerProfile.query.all()
    print(f"\nPLAYER PROFILES: {len(profiles)} total")
    
    # Check tournaments by status
    tournaments = Tournament.query.all()
    print(f"\nTOURNAMENTS: {len(tournaments)} total")
    
    # IMPORTANT: Debug the exact enum values being stored
    print("\nTournament Status Values in Database:")
    for t in tournaments:
        print(f"  - ID: {t.id}, Name: {t.name}, Status: {t.status}, Enum value: {t.status.value}")
    
    # Check the status enum itself
    print("\nTournamentStatus enum values:")
    for status in TournamentStatus:
        print(f"  - {status.name}: {status.value}")
    
    # Check tournaments by status with raw values
    upcoming_count = Tournament.query.filter_by(status=TournamentStatus.UPCOMING).count()
    ongoing_count = Tournament.query.filter_by(status=TournamentStatus.ONGOING).count()
    completed_count = Tournament.query.filter_by(status=TournamentStatus.COMPLETED).count()
    
    print(f"\nTOURNAMENT STATUS COUNTS:")
    print(f"  - UPCOMING: {upcoming_count}")
    print(f"  - ONGOING: {ongoing_count}")
    print(f"  - COMPLETED: {completed_count}")
    
    # Try direct string value comparison to debug
    raw_upcoming = db.session.query(Tournament).filter(Tournament.status == "upcoming").count()
    raw_ongoing = db.session.query(Tournament).filter(Tournament.status == "ongoing").count()
    raw_completed = db.session.query(Tournament).filter(Tournament.status == "completed").count()
    
    print(f"\nRAW STRING STATUS COUNTS:")
    print(f"  - 'upcoming': {raw_upcoming}")
    print(f"  - 'ongoing': {raw_ongoing}")
    print(f"  - 'completed': {raw_completed}")
    
    # Check tournament categories
    categories = TournamentCategory.query.all()
    print(f"\nTOURNAMENT CATEGORIES: {len(categories)} total")
    for category_type in CategoryType:
        count = TournamentCategory.query.filter_by(category_type=category_type).count()
        print(f"  - {category_type.name}: {count}")
    
    # Check registrations
    registrations = Registration.query.all()
    print(f"\nREGISTRATIONS: {len(registrations)} total")
    
    # Check player rankings
    print("\nTOP PLAYERS BY CATEGORY:")
    
    # Debug output for all players with points
    print("\nAll players with mens_singles_points:")
    all_singles = PlayerProfile.query.filter(PlayerProfile.mens_singles_points > 0).order_by(PlayerProfile.mens_singles_points.desc()).all()
    for p in all_singles:
        print(f"  - {p.full_name}: {p.mens_singles_points} points")
    
    # Try to get top 5 by points
    top_mens_singles = PlayerProfile.query.order_by(PlayerProfile.mens_singles_points.desc()).limit(5).all()
    print(f"\nTOP MEN'S SINGLES: {len(top_mens_singles)}")
    for player in top_mens_singles:
        print(f"  - {player.full_name}: {player.mens_singles_points} points")
    
    top_womens_singles = PlayerProfile.query.order_by(PlayerProfile.womens_singles_points.desc()).limit(5).all()
    print(f"\nTOP WOMEN'S SINGLES: {len(top_womens_singles)}")
    for player in top_womens_singles:
        print(f"  - {player.full_name}: {player.womens_singles_points} points")
    
    print("\n" + "="*80)
    print("DATABASE CHECK COMPLETE")
    print("="*80 + "\n")

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        check_database()