import pytest
from flask import url_for, session
from app import db
from app.models import User, PlayerProfile, UserRole, Tournament, TournamentStatus, TournamentCategory, Registration, Match, Team
from datetime import date, timedelta, datetime

# --- Reusable Helper Functions (Consider moving to a shared conftest or helpers file later) ---

def register_test_user(client, username, email, password):
    """Registers a basic player user."""
    return client.post(url_for('auth.register'), data={
        'username': username,
        'email': email,
        'password': password,
        'password2': password
    }, follow_redirects=True)

def login_test_user(client, email, password):
    """Logs in a user."""
    return client.post(url_for('auth.login'), data={
        'email': email,
        'password': password,
        'remember_me': False
    }, follow_redirects=True)

def create_player_profile(client, user_id, full_name="Test Player", bio="Test Bio"):
    """Creates a player profile for the logged-in user."""
    # Assumes user is already logged in
    # Note: This simulates posting to the create_profile route.
    # We need the actual create_profile route implementation to test this properly.
    # For now, we'll create the profile directly in the DB for testing dashboard access.
    profile = PlayerProfile(user_id=user_id, full_name=full_name, bio=bio)
    db.session.add(profile)
    db.session.commit()
    return profile

# --- Test Cases ---

def test_dashboard_access_denied_not_logged_in(client):
    """Test accessing /player/dashboard without being logged in."""
    response = client.get(url_for('player.dashboard'), follow_redirects=False) # Don't follow redirect yet
    assert response.status_code == 302 # Should redirect
    assert url_for('auth.login') in response.location # Should redirect to login

    response_redirected = client.get(url_for('player.dashboard'), follow_redirects=True)
    assert response_redirected.status_code == 200
    assert b"Sign In" in response_redirected.data # Should show login page

def test_dashboard_redirect_to_create_profile(client, init_database):
    """Test accessing dashboard redirects to create_profile if user has no profile."""
    # Register and login a user, but DO NOT create a profile
    register_test_user(client, 'noprofileuser', 'noprofile@test.com', 'password123')
    login_test_user(client, 'noprofile@test.com', 'password123')

    response = client.get(url_for('player.dashboard'), follow_redirects=False) # Don't follow redirect yet
    assert response.status_code == 302
    # Assuming the profile creation route is 'player.create_profile'
    assert url_for('player.create_profile') in response.location

    # Check flash message after redirect (need to simulate the redirect)
    # This requires the create_profile route to exist and render a template
    # For now, just check the redirect location.
    # TODO: Enhance this test when player.create_profile route is tested/available.
    # response_redirected = client.get(url_for('player.dashboard'), follow_redirects=True)
    # assert b"Please complete your player profile first." in response_redirected.data

def test_dashboard_basic_access_with_profile(client, init_database):
    """Test basic dashboard access for a user with a profile but no data."""
    # Register, login, and create profile
    register_test_user(client, 'profileuser', 'profile@test.com', 'password123')
    login_test_user(client, 'profile@test.com', 'password123')
    user = User.query.filter_by(email='profile@test.com').first()
    create_player_profile(client, user.id, full_name="Profiled Player")

    response = client.get(url_for('player.dashboard'))
    assert response.status_code == 200
    assert b"Player Dashboard" in response.data
    assert b"Profiled Player" in response.data # Check profile name is displayed
    # Check for sections, likely showing "No upcoming tournaments", "No match history", etc.
    assert b"Upcoming Tournaments" in response.data
    assert b"Ongoing Tournaments" in response.data
    assert b"Past Tournaments" in response.data
    assert b"Match History" in response.data
    assert b"Statistics" in response.data
    # Check specific "no data" messages if the template has them
    # assert b"You have no upcoming registrations." in response.data # Example

def test_dashboard_with_data(client, init_database):
    """Test dashboard displays data correctly (tournaments, matches, stats)."""
    # 1. Setup User and Profile
    register_test_user(client, 'datauser', 'data@test.com', 'password123')
    login_test_user(client, 'data@test.com', 'password123')
    user = User.query.filter_by(email='data@test.com').first()
    profile = create_player_profile(client, user.id, full_name="Data Player")
    # Add a partner for doubles
    partner_user = User(username='partner', email='partner@test.com', role=UserRole.PLAYER)
    partner_profile = PlayerProfile(user=partner_user, full_name="Partner Player")
    db.session.add_all([partner_user, partner_profile])
    db.session.commit() # Commit partner before using ID

    # 2. Setup Tournaments & Categories
    today = date.today()
    now = datetime.utcnow()
    upcoming_t = Tournament(id=1, name="Upcoming Open", start_date=today + timedelta(days=10), end_date=today + timedelta(days=12), status=TournamentStatus.UPCOMING)
    ongoing_t = Tournament(id=2, name="Ongoing Major", start_date=today - timedelta(days=1), end_date=today + timedelta(days=1), status=TournamentStatus.ONGOING)
    past_t = Tournament(id=3, name="Past Classic", start_date=today - timedelta(days=20), end_date=today - timedelta(days=18), status=TournamentStatus.COMPLETED)
    db.session.add_all([upcoming_t, ongoing_t, past_t])
    db.session.commit() # Commit tournaments before adding categories

    upcoming_c = TournamentCategory(id=1, name="Upcoming Singles", tournament_id=upcoming_t.id)
    ongoing_c = TournamentCategory(id=2, name="Ongoing Doubles", tournament_id=ongoing_t.id, category_type=CategoryType.MENS_DOUBLES) # Assuming CategoryType enum exists
    past_c = TournamentCategory(id=3, name="Past Singles", tournament_id=past_t.id)
    db.session.add_all([upcoming_c, ongoing_c, past_c])
    db.session.commit() # Commit categories before registrations/matches

    # 3. Setup Registrations
    reg_upcoming = Registration(id=1, player_id=profile.id, category_id=upcoming_c.id, payment_status='paid', payment_verified=True)
    # Doubles registration (user is player 1, responsible for payment)
    reg_ongoing = Registration(id=2, player_id=profile.id, partner_id=partner_profile.id, category_id=ongoing_c.id, payment_status='uploaded', payment_verified=False)
    reg_past = Registration(id=3, player_id=profile.id, category_id=past_c.id, payment_status='paid', payment_verified=True)
    # Add another registration with rejected payment
    reg_rejected = Registration(id=4, player_id=profile.id, category_id=past_c.id, payment_status='rejected', payment_verified=False) # Another registration in past event
    db.session.add_all([reg_upcoming, reg_ongoing, reg_past, reg_rejected])

    # 4. Setup Matches
    # Upcoming Match (Singles) - Should be 'next_match'
    match_next = Match(id=1, category_id=upcoming_c.id, player1_id=profile.id, scheduled_time=now + timedelta(hours=2), completed=False)
    # Ongoing Match (Doubles) - Part of history
    team1 = Team(id=1, category_id=ongoing_c.id, player1_id=profile.id, player2_id=partner_profile.id)
    team2 = Team(id=2, category_id=ongoing_c.id) # Opponent team
    db.session.add_all([team1, team2])
    db.session.commit() # Commit teams before match
    match_ongoing = Match(id=2, category_id=ongoing_c.id, team1_id=team1.id, team2_id=team2.id, scheduled_time=now - timedelta(hours=1), completed=False) # Still ongoing
    # Past Match (Singles) - Part of history, player won
    match_past = Match(id=3, category_id=past_c.id, player1_id=profile.id, scheduled_time=now - timedelta(days=19), completed=True, winner_id=profile.id) # Assuming player ID used for winner in singles
    db.session.add_all([match_next, match_ongoing, match_past])

    # 5. Update Profile Stats (Simulated)
    profile.matches_won = 1
    profile.matches_lost = 0 # Assuming only one completed match so far
    profile.mens_singles_points = 100 # Points from past tournament
    db.session.add(profile)
    db.session.commit()

    # 6. Make Request and Assert
    response = client.get(url_for('player.dashboard'))
    assert response.status_code == 200
    assert b"Player Dashboard" in response.data
    assert b"Data Player" in response.data

    # Check Tournaments
    assert b"Upcoming Open" in response.data
    assert b"Ongoing Major" in response.data
    assert b"Past Classic" in response.data

    # Check Match History (Order: ongoing, past)
    assert response.data.find(b"Ongoing Doubles") < response.data.find(b"Past Singles") # Check category names appear in history
    # Check Next Match
    assert b"Next Match" in response.data
    assert b"Upcoming Singles" in response.data # Category of the next match

    # Check Stats
    assert b"Total Tournaments: 3" in response.data # Counts unique tournaments registered for
    assert b"Completed: 1" in response.data
    assert b"Upcoming: 1" in response.data
    assert b"Pending Payments: 1" in response.data # From ongoing doubles reg
    assert b"Rejected Payments: 1" in response.data # From extra past reg
    assert b"Matches Won: 1" in response.data
    assert b"Matches Lost: 0" in response.data
    assert b"Win/Loss Ratio: 100.0%" in response.data # Calculated from 1 win, 0 loss
    assert b"Total Points: 100" in response.data # Assuming get_points sums relevant fields

    # Clean up (optional, as init_database handles it, but good practice if needed)
    # db.session.delete(...)
    # db.session.commit()