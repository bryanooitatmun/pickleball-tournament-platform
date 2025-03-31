import pytest
from flask import url_for, session
from app import db, socketio
from app.models import User, PlayerProfile, UserRole, Tournament, TournamentStatus, TournamentCategory, Registration, Match, Team, MatchScore, CategoryType
from datetime import date, timedelta, datetime
from unittest.mock import patch

# --- Reusable Helper Functions (Consider refactoring to conftest) ---

def register_test_user(client, username, email, password):
    return client.post(url_for('auth.register'), data={
        'username': username, 'email': email, 'password': password, 'password2': password
    }, follow_redirects=True)

def login_test_user(client, email, password):
    return client.post(url_for('auth.login'), data={
        'email': email, 'password': password, 'remember_me': False
    }, follow_redirects=True)

def create_test_profile(user_id, full_name="Test Player"):
    profile = PlayerProfile(user_id=user_id, full_name=full_name)
    db.session.add(profile)
    db.session.commit()
    return profile

def create_test_tournament(id, name="Test Tournament", status=TournamentStatus.ONGOING):
    tournament = Tournament(id=id, name=name, status=status, start_date=date.today(), end_date=date.today() + timedelta(days=1))
    db.session.add(tournament)
    db.session.commit()
    return tournament

def create_test_category(id, tournament_id, name="Test Category", category_type=CategoryType.MENS_SINGLES):
    category = TournamentCategory(id=id, tournament_id=tournament_id, name=name, category_type=category_type)
    db.session.add(category)
    db.session.commit()
    return category

def create_test_match(id, category_id, player1_id=None, player2_id=None, team1_id=None, team2_id=None, is_doubles=False, referee_verified=False, player_verified=False, completed=False, scores=None):
    match = Match(
        id=id,
        category_id=category_id,
        player1_id=player1_id,
        player2_id=player2_id,
        team1_id=team1_id,
        team2_id=team2_id,
        is_doubles=is_doubles,
        referee_verified=referee_verified,
        player_verified=player_verified,
        completed=completed
    )
    db.session.add(match)
    db.session.commit() # Commit match first to get ID for scores
    if scores:
        for i, score_data in enumerate(scores):
            score = MatchScore(match_id=match.id, set_number=i+1, team1_score=score_data[0], team2_score=score_data[1])
            db.session.add(score)
        db.session.commit()
    return match

# --- Test Cases for /match/<id>/verify ---

def test_verify_match_access_denied_not_logged_in(client, init_database):
    """Test accessing verify_match without being logged in."""
    # Need a dummy match to generate URL
    t = create_test_tournament(1)
    c = create_test_category(1, t.id)
    m = create_test_match(1, c.id)
    response = client.post(url_for('player.verify_match', match_id=m.id), follow_redirects=False)
    assert response.status_code == 302
    assert url_for('auth.login') in response.location

def test_verify_match_fail_no_profile(client, init_database):
    """Test verifying match fails if user has no profile."""
    register_test_user(client, 'verify_np', 'verify_np@test.com', 'password123')
    login_test_user(client, 'verify_np@test.com', 'password123')
    # DO NOT create profile

    t = create_test_tournament(1)
    c = create_test_category(1, t.id)
    m = create_test_match(1, c.id) # Match doesn't need players for this test

    response = client.post(url_for('player.verify_match', match_id=m.id), follow_redirects=True)
    assert response.status_code == 200 # Redirects to match detail
    assert b'You need a player profile to verify match results.' in response.data
    # Check we are on match detail page (adjust assertion based on template)
    assert f'Match {m.id}'.encode('utf-8') in response.data or b'Match Details' in response.data

def test_verify_match_fail_match_not_found(client, init_database):
    """Test verifying a non-existent match returns 404."""
    register_test_user(client, 'verify_user', 'verify@test.com', 'password123')
    login_test_user(client, 'verify@test.com', 'password123')
    user = User.query.filter_by(email='verify@test.com').first()
    create_test_profile(user.id)

    response = client.post(url_for('player.verify_match', match_id=999))
    assert response.status_code == 404

def test_verify_match_fail_not_referee_verified(client, init_database):
    """Test verifying match fails if referee hasn't verified it yet."""
    register_test_user(client, 'verify_user', 'verify@test.com', 'password123')
    login_test_user(client, 'verify@test.com', 'password123')
    user = User.query.filter_by(email='verify@test.com').first()
    profile = create_test_profile(user.id)

    t = create_test_tournament(1)
    c = create_test_category(1, t.id)
    # Match involves the logged-in user, but referee_verified is False
    m = create_test_match(1, c.id, player1_id=profile.id, referee_verified=False, scores=[(6,4)])

    response = client.post(url_for('player.verify_match', match_id=m.id), follow_redirects=True)
    assert response.status_code == 200 # Redirects to match detail
    assert b'This match must be verified by a referee before player verification.' in response.data
    assert m.player_verified is False # Check status didn't change

def test_verify_match_fail_no_scores(client, init_database):
    """Test verifying match fails if there are no scores."""
    register_test_user(client, 'verify_user', 'verify@test.com', 'password123')
    login_test_user(client, 'verify@test.com', 'password123')
    user = User.query.filter_by(email='verify@test.com').first()
    profile = create_test_profile(user.id)

    t = create_test_tournament(1)
    c = create_test_category(1, t.id)
    # Match involves user, referee verified, but no scores added
    m = create_test_match(1, c.id, player1_id=profile.id, referee_verified=True, scores=None)

    response = client.post(url_for('player.verify_match', match_id=m.id), follow_redirects=True)
    assert response.status_code == 200 # Redirects to match detail
    assert b'Match must be completed with scores before verification.' in response.data
    assert m.player_verified is False

def test_verify_match_fail_not_authorized(client, init_database):
    """Test verifying match fails if logged-in user is not part of the match."""
    # User 1 (logged in)
    register_test_user(client, 'verify_user', 'verify@test.com', 'password123')
    login_test_user(client, 'verify@test.com', 'password123')
    user1 = User.query.filter_by(email='verify@test.com').first()
    profile1 = create_test_profile(user1.id, full_name="Verifier")

    # User 2 & 3 (players in the match)
    user2 = User(username='playerA', email='pa@test.com'); db.session.add(user2); db.session.commit()
    profile2 = create_test_profile(user2.id, full_name="Player A")
    user3 = User(username='playerB', email='pb@test.com'); db.session.add(user3); db.session.commit()
    profile3 = create_test_profile(user3.id, full_name="Player B")

    t = create_test_tournament(1)
    c = create_test_category(1, t.id)
    # Match involves player A and B, referee verified
    m = create_test_match(1, c.id, player1_id=profile2.id, player2_id=profile3.id, referee_verified=True, scores=[(6,4)])

    # Logged-in user (Verifier) tries to verify
    response = client.post(url_for('player.verify_match', match_id=m.id), follow_redirects=True)
    assert response.status_code == 200 # Redirects to match detail
    assert b'You are not authorized to verify this match.' in response.data
    assert m.player_verified is False

@patch('app.player.match_routes.socketio.emit') # Mock socketio emit
@patch('app.player.match_routes.BracketService.advance_winner') # Mock bracket service
def test_verify_match_success_singles(mock_advance_winner, mock_socketio_emit, client, init_database):
    """Test successful verification of a singles match by a player."""
    # Setup users and profiles
    register_test_user(client, 'player1_verify', 'p1v@test.com', 'password123')
    login_test_user(client, 'p1v@test.com', 'password123') # Login as player 1
    user1 = User.query.filter_by(email='p1v@test.com').first()
    profile1 = create_test_profile(user1.id, full_name="Player 1 Verify")
    user2 = User(username='player2_verify', email='p2v@test.com'); db.session.add(user2); db.session.commit()
    profile2 = create_test_profile(user2.id, full_name="Player 2 Verify")

    # Setup tournament, category, and match
    t = create_test_tournament(1)
    c = create_test_category(1, t.id)
    # Match involves player 1, referee verified, has scores
    m = create_test_match(
        id=1, category_id=c.id, player1_id=profile1.id, player2_id=profile2.id,
        referee_verified=True, scores=[(6,4), (6,3)], winner_id=profile1.id # Player 1 won
    )
    # Simulate a next match for bracket advancement check
    m.next_match_id = 2
    db.session.add(m)
    db.session.commit()

    # Perform verification (logged in as player 1)
    response = client.post(url_for('player.verify_match', match_id=m.id), follow_redirects=True)

    assert response.status_code == 200 # Redirects to match detail
    assert b'Match result successfully verified.' in response.data
    assert b'Winner has been advanced to the next round.' in response.data # Check advancement flash

    # Verify match status in DB
    db.session.refresh(m)
    assert m.player_verified is True
    assert m.completed is True # Should be set to true on verification

    # Verify mocks were called
    mock_socketio_emit.assert_called_once()
    # Check emit arguments (basic check for event name and room)
    args, kwargs = mock_socketio_emit.call_args
    assert args[0] == 'match_updated'
    assert 'room' in kwargs and kwargs['room'] == f'tournament_{t.id}'

    mock_advance_winner.assert_called_once_with(m) # Check service was called with the match object

@patch('app.player.match_routes.socketio.emit')
@patch('app.player.match_routes.BracketService.advance_winner')
def test_verify_match_success_doubles_captain(mock_advance_winner, mock_socketio_emit, client, init_database):
    """Test successful verification of a doubles match by team captain (player1)."""
    # Setup users and profiles
    register_test_user(client, 'captain', 'cap@test.com', 'password123')
    login_test_user(client, 'cap@test.com', 'password123') # Login as captain
    user_cap = User.query.filter_by(email='cap@test.com').first()
    profile_cap = create_test_profile(user_cap.id, full_name="Team Captain")
    user_partner = User(username='partner', email='part@test.com'); db.session.add(user_partner); db.session.commit()
    profile_partner = create_test_profile(user_partner.id, full_name="Team Partner")
    # Opponent team
    user_opp1 = User(username='opp1', email='opp1@test.com'); db.session.add(user_opp1); db.session.commit()
    profile_opp1 = create_test_profile(user_opp1.id, full_name="Opponent 1")
    user_opp2 = User(username='opp2', email='opp2@test.com'); db.session.add(user_opp2); db.session.commit()
    profile_opp2 = create_test_profile(user_opp2.id, full_name="Opponent 2")

    # Setup teams
    team1 = Team(id=1, player1_id=profile_cap.id, player2_id=profile_partner.id) # Captain is player1
    team2 = Team(id=2, player1_id=profile_opp1.id, player2_id=profile_opp2.id)
    db.session.add_all([team1, team2])
    db.session.commit()

    # Setup tournament, category, and match
    t = create_test_tournament(1)
    c = create_test_category(1, t.id, category_type=CategoryType.MENS_DOUBLES)
    m = create_test_match(
        id=1, category_id=c.id, team1_id=team1.id, team2_id=team2.id, is_doubles=True,
        referee_verified=True, scores=[(6,4)], winner_id=team1.id # Team 1 won
    )
    db.session.add(m)
    db.session.commit()

    # Perform verification (logged in as captain)
    response = client.post(url_for('player.verify_match', match_id=m.id), follow_redirects=True)

    assert response.status_code == 200
    assert b'Match result successfully verified.' in response.data
    # No advancement flash if next_match_id is None

    # Verify match status
    db.session.refresh(m)
    assert m.player_verified is True
    assert m.completed is True

    # Verify mocks
    mock_socketio_emit.assert_called_once()
    mock_advance_winner.assert_not_called() # Not called because next_match_id is None

def test_verify_match_fail_doubles_non_captain(client, init_database):
    """Test verification fails for doubles match if logged in as non-captain (player2)."""
    # Setup users and profiles
    user_cap = User(username='captain2', email='cap2@test.com'); db.session.add(user_cap); db.session.commit()
    profile_cap = create_test_profile(user_cap.id, full_name="Team Captain 2")
    register_test_user(client, 'partner2', 'part2@test.com', 'password123')
    login_test_user(client, 'part2@test.com', 'password123') # Login as partner
    user_partner = User.query.filter_by(email='part2@test.com').first()
    profile_partner = create_test_profile(user_partner.id, full_name="Team Partner 2")
    # Opponent team
    user_opp1 = User(username='opp1b', email='opp1b@test.com'); db.session.add(user_opp1); db.session.commit()
    profile_opp1 = create_test_profile(user_opp1.id, full_name="Opponent 1b")
    user_opp2 = User(username='opp2b', email='opp2b@test.com'); db.session.add(user_opp2); db.session.commit()
    profile_opp2 = create_test_profile(user_opp2.id, full_name="Opponent 2b")

    # Setup teams
    team1 = Team(id=1, player1_id=profile_cap.id, player2_id=profile_partner.id) # Logged-in user is player2
    team2 = Team(id=2, player1_id=profile_opp1.id, player2_id=profile_opp2.id)
    db.session.add_all([team1, team2])
    db.session.commit()

    # Setup tournament, category, and match
    t = create_test_tournament(1)
    c = create_test_category(1, t.id, category_type=CategoryType.MENS_DOUBLES)
    m = create_test_match(
        id=1, category_id=c.id, team1_id=team1.id, team2_id=team2.id, is_doubles=True,
        referee_verified=True, scores=[(6,4)], winner_id=team1.id
    )
    db.session.add(m)
    db.session.commit()

    # Perform verification (logged in as partner/player2)
    response = client.post(url_for('player.verify_match', match_id=m.id), follow_redirects=True)

    assert response.status_code == 200
    assert b'You are not authorized to verify this match.' in response.data # Should fail authorization
    db.session.refresh(m)
    assert m.player_verified is False # Status unchanged

# --- Test Cases for /api/next_match ---

def test_api_next_match_success_singles(client, init_database):
    """Test API returns the next upcoming singles match."""
    # Setup user, profile, tournament, category
    register_test_user(client, 'nextmatchuser', 'next@test.com', 'password123')
    login_test_user(client, 'next@test.com', 'password123')
    user = User.query.filter_by(email='next@test.com').first()
    profile = create_test_profile(user.id, full_name="Next Match User")
    opponent = User(username='opp_next', email='opp_n@test.com'); db.session.add(opponent); db.session.commit()
    profile_opp = create_test_profile(opponent.id, full_name="Opponent Next")
    t = create_test_tournament(1, name="Next Match Tourney")
    c = create_test_category(1, t.id, name="Next Singles")

    # Create matches: one past, one future (next), one further future
    now = datetime.utcnow()
    past_match = create_test_match(1, c.id, player1_id=profile.id, player2_id=profile_opp.id, completed=True, scheduled_time=now - timedelta(days=1))
    next_match = create_test_match(2, c.id, player1_id=profile_opp.id, player2_id=profile.id, completed=False, scheduled_time=now + timedelta(hours=1), court="Court 5")
    future_match = create_test_match(3, c.id, player1_id=profile.id, player2_id=profile_opp.id, completed=False, scheduled_time=now + timedelta(hours=5))

    response = client.get(url_for('player.get_next_match'))
    assert response.status_code == 200
    json_data = response.get_json()

    assert json_data['id'] == next_match.id
    assert json_data['tournament_name'] == "Next Match Tourney"
    assert json_data['category_name'] == "Next Singles"
    assert json_data['court'] == "Court 5"
    assert json_data['opponent'] == "Opponent Next"
    # Check time formatting (adjust if format changes in route)
    assert json_data['scheduled_time'] == (now + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M')

def test_api_next_match_success_doubles(client, init_database):
    """Test API returns the next upcoming doubles match."""
    # Setup user, partner, opponents, teams, etc.
    register_test_user(client, 'nextd_user', 'nextd@test.com', 'password123')
    login_test_user(client, 'nextd@test.com', 'password123')
    user = User.query.filter_by(email='nextd@test.com').first()
    profile = create_test_profile(user.id, full_name="Next Doubles User")
    partner = User(username='nextd_part', email='nextd_p@test.com'); db.session.add(partner); db.session.commit()
    profile_part = create_test_profile(partner.id, full_name="Next Doubles Partner")
    opp1 = User(username='nextd_opp1', email='nextd_o1@test.com'); db.session.add(opp1); db.session.commit()
    profile_opp1 = create_test_profile(opp1.id, full_name="Next D Opponent 1")
    opp2 = User(username='nextd_opp2', email='nextd_o2@test.com'); db.session.add(opp2); db.session.commit()
    profile_opp2 = create_test_profile(opp2.id, full_name="Next D Opponent 2")

    team1 = Team(id=1, player1_id=profile.id, player2_id=profile_part.id)
    team2 = Team(id=2, player1_id=profile_opp1.id, player2_id=profile_opp2.id)
    db.session.add_all([team1, team2])
    db.session.commit()

    t = create_test_tournament(1, name="Next Doubles Tourney")
    c = create_test_category(1, t.id, name="Next Doubles", category_type=CategoryType.MENS_DOUBLES)

    # Create matches
    now = datetime.utcnow()
    next_match = create_test_match(1, c.id, team1_id=team1.id, team2_id=team2.id, is_doubles=True, completed=False, scheduled_time=now + timedelta(minutes=30), court="Court D")

    response = client.get(url_for('player.get_next_match'))
    assert response.status_code == 200
    json_data = response.get_json()

    assert json_data['id'] == next_match.id
    assert json_data['tournament_name'] == "Next Doubles Tourney"
    assert json_data['category_name'] == "Next Doubles"
    assert json_data['court'] == "Court D"
    assert json_data['opponent'] == "Next D Opponent 1/Next D Opponent 2" # Check opponent formatting
    assert json_data['scheduled_time'] == (now + timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M')

def test_api_next_match_none_found(client, init_database):
    """Test API returns 404 when no upcoming matches exist."""
    register_test_user(client, 'nomatchuser', 'nomatch@test.com', 'password123')
    login_test_user(client, 'nomatch@test.com', 'password123')
    user = User.query.filter_by(email='nomatch@test.com').first()
    create_test_profile(user.id)

    # Create only a past match
    t = create_test_tournament(1)
    c = create_test_category(1, t.id)
    past_match = create_test_match(1, c.id, player1_id=user.player_profile.id, completed=True, scheduled_time=datetime.utcnow() - timedelta(days=1))

    response = client.get(url_for('player.get_next_match'))
    assert response.status_code == 404
    json_data = response.get_json()
    assert json_data['message'] == 'No upcoming matches found'

def test_api_next_match_no_profile(client, init_database):
    """Test API returns 404 if user has no profile."""
    register_test_user(client, 'apinpuser', 'apinp@test.com', 'password123')
    login_test_user(client, 'apinp@test.com', 'password123')
    # No profile created

    response = client.get(url_for('player.get_next_match'))
    assert response.status_code == 404
    json_data = response.get_json()
    assert json_data['error'] == 'No player profile found'

def test_api_next_match_not_logged_in(client, init_database):
    """Test API requires login."""
    response = client.get(url_for('player.get_next_match'), follow_redirects=False)
    assert response.status_code == 302 # Redirects to login
    assert url_for('auth.login') in response.location