"""
Simple test script to verify database access and create a test tournament.
This can help identify issues with empty query results.
"""

from app import create_app, db
from app.models import Tournament, User, UserRole, TournamentTier, TournamentFormat, TournamentStatus
from datetime import datetime, timedelta

def test_database_access():
    print("Testing database access...")
    
    # First, check if we can query users
    users = User.query.all()
    print(f"Found {len(users)} users")
    
    # Try to find at least one admin user
    admin = User.query.filter_by(role=UserRole.ADMIN).first()
    organizer_id = 1  # Default fallback
    
    if admin:
        print(f"Found admin user: {admin.username} (ID: {admin.id})")
        organizer_id = admin.id
    else:
        # Try to find an organizer
        organizer = User.query.filter_by(role=UserRole.ORGANIZER).first()
        if organizer:
            print(f"Found organizer user: {organizer.username} (ID: {organizer.id})")
            organizer_id = organizer.id
        else:
            print("No admin or organizer found, using default ID: 1")
    
    # Check existing tournaments
    existing_tournaments = Tournament.query.all()
    print(f"Found {len(existing_tournaments)} existing tournaments")
    for t in existing_tournaments:
        print(f"  - ID: {t.id}, Name: {t.name}, Status: {t.status}")
    
    # Create a new test tournament
    print("\nCreating a test tournament...")
    
    test_tournament = Tournament(
        name=f"Test Tournament {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        organizer_id=organizer_id,
        location="Test Location",
        description="A test tournament to verify database access",
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=3),
        registration_deadline=datetime.utcnow() - timedelta(days=7),
        tier=TournamentTier.OPEN,
        format=TournamentFormat.SINGLE_ELIMINATION,
        status=TournamentStatus.UPCOMING,
        prize_pool=1000.0,
        registration_fee=50.0
    )
    
    db.session.add(test_tournament)
    db.session.commit()
    print(f"Created test tournament with ID: {test_tournament.id}")
    
    # Now query all tournaments again to verify it was saved
    tournaments_after = Tournament.query.all()
    print(f"Now found {len(tournaments_after)} tournaments")
    
    # Verify the specific tournament we just added
    specific_tournament = Tournament.query.get(test_tournament.id)
    if specific_tournament:
        print(f"Successfully retrieved the test tournament by ID: {specific_tournament.name}")
    else:
        print("ERROR: Could not retrieve the test tournament by ID!")
    
    # Try filtering by status
    upcoming_tournaments = Tournament.query.filter_by(status=TournamentStatus.UPCOMING).all()
    print(f"Found {len(upcoming_tournaments)} upcoming tournaments")
    
    print("\nTest completed!")

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        test_database_access()