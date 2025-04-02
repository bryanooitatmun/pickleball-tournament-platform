import pytest
from flask import url_for
from app import db
from app.models import Tournament, TournamentStatus
from datetime import date, timedelta

def test_events_route_no_tournaments(client, init_database):
    """Test the /events route when there are no tournaments."""
    response = client.get(url_for('main.events'))
    assert response.status_code == 200
    assert b"Upcoming Events" in response.data
    assert b"Past Events" in response.data
    # Check that no tournament data is displayed (adjust based on actual template structure)
    assert b"No upcoming events scheduled." in response.data # Assuming template has this message
    assert b"No past events found." in response.data # Assuming template has this message

def test_events_route_with_tournaments(client, init_database):
    """Test the /events route with upcoming and past tournaments."""
    # Create test tournaments
    today = date.today()
    upcoming_tournament = Tournament(
        name="Upcoming Grand Slam",
        start_date=today + timedelta(days=10),
        end_date=today + timedelta(days=12),
        registration_deadline=today + timedelta(days=5),
        status=TournamentStatus.UPCOMING,
        tier="Tier 1" # Assuming tier is required
    )
    past_tournament = Tournament(
        name="Past Championship",
        start_date=today - timedelta(days=20),
        end_date=today - timedelta(days=18),
        registration_deadline=today - timedelta(days=25),
        status=TournamentStatus.COMPLETED,
        tier="Tier 2" # Assuming tier is required
    )
    db.session.add_all([upcoming_tournament, past_tournament])
    db.session.commit()

    response = client.get(url_for('main.events'))
    assert response.status_code == 200
    assert b"Upcoming Events" in response.data
    assert b"Past Events" in response.data

    # Check if tournament names are present
    assert b"Upcoming Grand Slam" in response.data
    assert b"Past Championship" in response.data

    # Check if month grouping is present (e.g., based on start/end date month)
    upcoming_month = (today + timedelta(days=10)).strftime('%B').upper()
    past_month = (today - timedelta(days=18)).strftime('%B').upper()
    assert bytes(upcoming_month, 'utf-8') in response.data
    assert bytes(past_month, 'utf-8') in response.data

    # Check for tier legend/info
    assert b"Tier 1" in response.data
    assert b"Tier 2" in response.data

def test_sponsors_route_no_sponsors(client, init_database):
    """Test the /sponsors route when there are no sponsors."""
    response = client.get(url_for('main.sponsors'))
    assert response.status_code == 200
    assert b"Our Sponsors" in response.data
    # Check that no sponsor data is displayed (adjust based on actual template)
    assert b"No sponsors to display." in response.data # Assuming template has this message

def test_sponsors_route_with_sponsors(client, init_database):
    """Test the /sponsors route with platform sponsors."""
    from app.models import PlatformSponsor # Import inside test or at top
    sponsor1 = PlatformSponsor(name="Pickleball Pro Gear", website="https://progear.com", logo_url="logo1.png")
    sponsor2 = PlatformSponsor(name="Court Kings", website="https://courtkings.com", logo_url="logo2.png")
    db.session.add_all([sponsor1, sponsor2])
    db.session.commit()

    response = client.get(url_for('main.sponsors'))
    assert response.status_code == 200
    assert b"Our Sponsors" in response.data
    assert b"Pickleball Pro Gear" in response.data
    assert b"Court Kings" in response.data
    assert b"https://progear.com" in response.data # Check if website link is present
    assert b"logo2.png" in response.data # Check if logo url is present

def test_tournament_detail_route_not_found(client, init_database):
    """Test the /tournament/<id> route for a non-existent tournament."""
    response = client.get(url_for('main.tournament_detail', id=999))
    assert response.status_code == 404

def test_tournament_detail_route_upcoming(client, init_database):
    """Test the /tournament/<id> route for an upcoming tournament."""
    from app.models import Tournament, TournamentCategory, TournamentStatus
    from datetime import date, timedelta
    today = date.today()
    upcoming_tournament = Tournament(
        id=1,
        name="Future Fest",
        start_date=today + timedelta(days=10),
        end_date=today + timedelta(days=12),
        registration_deadline=today + timedelta(days=5),
        status=TournamentStatus.UPCOMING,
        tier="Tier 3"
    )
    category1 = TournamentCategory(id=1, name="Men's Singles", tournament=upcoming_tournament, display_order=1)
    db.session.add_all([upcoming_tournament, category1])
    db.session.commit()

    response = client.get(url_for('main.tournament_detail', id=1))
    assert response.status_code == 200
    assert b"Future Fest" in response.data
    assert b"Men's Singles" in response.data
    # Check that match/winner sections are likely not present or empty for upcoming
    assert b"Matches" not in response.data # Adjust based on template conditional logic
    assert b"Winner" not in response.data # Adjust based on template conditional logic

def test_tournament_detail_route_completed(client, init_database):
    """Test the /tournament/<id> route for a completed tournament with matches and winner."""
    from app.models import Tournament, TournamentCategory, TournamentStatus, Match, Team, User, PlayerProfile
    from datetime import date, timedelta
    today = date.today()

    # Create users and profiles
    user1 = User(id=1, username='player1', email='p1@test.com')
    profile1 = PlayerProfile(id=1, user=user1, full_name="Player One")
    user2 = User(id=2, username='player2', email='p2@test.com')
    profile2 = PlayerProfile(id=2, user=user2, full_name="Player Two")
    db.session.add_all([user1, profile1, user2, profile2])

    # Create tournament and category
    completed_tournament = Tournament(
        id=2,
        name="Past Glory",
        start_date=today - timedelta(days=20),
        end_date=today - timedelta(days=18),
        registration_deadline=today - timedelta(days=25),
        status=TournamentStatus.COMPLETED,
        tier="Tier 1"
    )
    category2 = TournamentCategory(id=2, name="Women's Singles", tournament=completed_tournament, display_order=1)
    db.session.add(completed_tournament) # Add tournament first
    db.session.flush() # Ensure tournament gets an ID if not explicitly set
    db.session.add(category2) # Add category associated with tournament

    # Create teams (even for singles, often represented as teams of 1)
    team1 = Team(id=1, category_id=category2.id, player1_id=profile1.id)
    team2 = Team(id=2, category_id=category2.id, player1_id=profile2.id)
    db.session.add_all([team1, team2])

    # Create a final match
    final_match = Match(
        id=1,
        category_id=category2.id,
        team1_id=team1.id,
        team2_id=team2.id,
        round=1, # Assuming round 1 is the final
        match_order=1,
        winner_id=team1.id, # Player One wins
        referee_verified=True,
        player_verified=True
    )
    db.session.add(final_match)
    db.session.commit()

    response = client.get(url_for('main.tournament_detail', id=2))
    assert response.status_code == 200
    assert b"Past Glory" in response.data
    assert b"Women's Singles" in response.data
    # Check if match details are present (e.g., player names)
    assert b"Player One" in response.data
    assert b"Player Two" in response.data
    # Check if winner is displayed (adjust based on template)
    assert b"Winner: Player One" in response.data # Example assertion

def test_player_detail_route_not_found(client, init_database):
    """Test the /player/<id> route for a non-existent player profile."""
    response = client.get(url_for('main.player_detail', id=999))
    assert response.status_code == 404

def test_player_detail_route_existing_player(client, init_database):
    """Test the /player/<id> route for an existing player."""
    from app.models import User, PlayerProfile, Equipment, PlayerSponsor, Registration, Tournament, TournamentCategory, TournamentStatus
    from datetime import date, timedelta

    # Create User and PlayerProfile
    user = User(id=3, username='player3', email='p3@test.com')
    profile = PlayerProfile(
        id=3,
        user=user,
        full_name="Player Three",
        bio="A rising star",
        mens_singles_points=150
    )
    db.session.add_all([user, profile])

    # Create related data (optional but good for testing display)
    equipment = Equipment(id=1, player_profile_id=profile.id, item_name="Super Paddle", brand="BrandX")
    sponsor = PlayerSponsor(id=1, player_profile_id=profile.id, sponsor_name="Local Shop", logo_url="shop.png")

    # Create a tournament and registration for recent activity
    tournament = Tournament(
        id=3,
        name="Local Open",
        start_date=date.today() - timedelta(days=5),
        end_date=date.today() - timedelta(days=3),
        status=TournamentStatus.COMPLETED
    )
    category = TournamentCategory(id=3, name="Men's Singles", tournament=tournament)
    registration = Registration(id=1, player_profile_id=profile.id, category=category)

    db.session.add_all([equipment, sponsor, tournament, category, registration])
    db.session.commit()

    response = client.get(url_for('main.player_detail', id=3))
    assert response.status_code == 200
    assert b"Player Three" in response.data
    assert b"A rising star" in response.data # Check bio
    assert b"150" in response.data # Check points (adjust based on how template displays)

    # Check for related data display
    assert b"Recent Tournaments" in response.data
    assert b"Local Open" in response.data
    assert b"Equipment" in response.data
    assert b"Super Paddle" in response.data
    assert b"BrandX" in response.data
    assert b"Sponsors" in response.data
    assert b"Local Shop" in response.data
    assert b"shop.png" in response.data # Check sponsor logo

def test_rankings_route_default(client, init_database):
    """Test the /rankings route default view (Men's Singles)."""
    from app.models import User, PlayerProfile
    # Create players with points
    user4 = User(id=4, username='player4', email='p4@test.com')
    profile4 = PlayerProfile(id=4, user=user4, full_name="Ranked Player A", mens_singles_points=200)
    user5 = User(id=5, username='player5', email='p5@test.com')
    profile5 = PlayerProfile(id=5, user=user5, full_name="Ranked Player B", mens_singles_points=300)
    user6 = User(id=6, username='player6', email='p6@test.com')
    profile6 = PlayerProfile(id=6, user=user6, full_name="Unranked Player C", womens_singles_points=100) # Different category
    db.session.add_all([user4, profile4, user5, profile5, user6, profile6])
    db.session.commit()

    response = client.get(url_for('main.rankings')) # Default is mens_singles
    assert response.status_code == 200
    assert b"Men's Singles Rankings" in response.data
    # Check players are present and ordered correctly (B then A)
    # Use response.data.find to check order
    assert response.data.find(b"Ranked Player B") < response.data.find(b"Ranked Player A")
    # Check ranks are displayed (adjust based on template)
    assert b"1." in response.data # Rank 1 for Player B
    assert b"2." in response.data # Rank 2 for Player A
    # Check unranked player (different category) is not shown
    assert b"Unranked Player C" not in response.data

def test_rankings_route_specific_category(client, init_database):
    """Test the /rankings route for a specific category (Women's Singles)."""
    from app.models import User, PlayerProfile
    # Use players created in previous test or create new ones if needed
    # Need player C from previous test
    profile6 = PlayerProfile.query.get(6) # Get existing player C
    user7 = User(id=7, username='player7', email='p7@test.com')
    profile7 = PlayerProfile(id=7, user=user7, full_name="Ranked Player D", womens_singles_points=150)
    user8 = User(id=8, username='player8', email='p8@test.com')
    profile8 = PlayerProfile(id=8, user=user8, full_name="Ranked Player E", womens_singles_points=50)
    db.session.add_all([user7, profile7, user8, profile8]) # Add new players
    db.session.commit()

    response = client.get(url_for('main.rankings', category='womens_singles'))
    assert response.status_code == 200
    assert b"Women's Singles Rankings" in response.data
    # Check players are present and ordered correctly (D then C then E)
    assert response.data.find(b"Ranked Player D") < response.data.find(b"Unranked Player C") < response.data.find(b"Ranked Player E")
    # Check ranks
    assert b"1." in response.data # Rank 1 for Player D
    assert b"2." in response.data # Rank 2 for Player C
    assert b"3." in response.data # Rank 3 for Player E

def test_rankings_route_empty_category(client, init_database):
    """Test the /rankings route for a category with no ranked players."""
    response = client.get(url_for('main.rankings', category='mixed_doubles'))
    assert response.status_code == 200
    assert b"Mixed Doubles Rankings" in response.data
    # Check for a message indicating no players (adjust based on template)
    assert b"No players found in this ranking category." in response.data # Example assertion

# TODO: Add test for ONGOING tournament status in tournament_detail