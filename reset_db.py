"""
Database reset and initialization script.
This script will drop all tables and recreate them, then run the seed script.
USE WITH CAUTION: This will delete all existing data!
"""

import os
import sys
from flask import Flask
from app import create_app, db
from app.models import User, PlayerProfile, Tournament, TournamentCategory, Registration, Match, MatchScore

def reset_database():
    print("WARNING: This will delete all data in the database!")
    confirm = input("Are you sure you want to continue? (y/n): ")
    
    if confirm.lower() != 'y':
        print("Operation cancelled.")
        return
    
    print("Dropping all tables...")
    db.drop_all()
    print("Creating all tables...")
    db.create_all()
    print("Database reset complete!")
    
    # Import and run seed script
    try:
        print("Running seed script...")
        from seed import seed_database
        seed_database()
        print("Seed completed!")
    except Exception as e:
        print(f"Error during seeding: {e}")

if __name__ == "__main__":
    print("Database Reset and Initialization Script")
    print("=======================================")
    
    app = create_app()
    with app.app_context():
        reset_database()