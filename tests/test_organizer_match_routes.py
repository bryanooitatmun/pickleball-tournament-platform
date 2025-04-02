import pytest
from flask import url_for, json
from app.models import (User, UserRole, Tournament, TournamentCategory, CategoryType,
                        TournamentFormat, Registration, Match, MatchScore, Team, TournamentStatus)
from tests.test_organizer_tournament_routes import create_test_tournament # Reuse helper
from tests.test_organizer_category_routes import create_test_category # Reuse helper
from datetime import datetime, time

# --- Helper Functions ---

def create_test_registration(db, user, category, seed=None, is_approved=True, payment_verified=True):
    """Helper to create a registration."""
    reg = Registration(
        user_id=user.id,
        category_id=category.id,
        team_name=f"{user.username}_Team",
        seed=seed,
        is_approved=is_approved,
        payment_verified=payment_verified,
        registration_date=datetime.utcnow()
    )
    db.session.add(reg)
    db.session.commit()
    return reg

def create_test_match(db, category, player1, player2=None, team1=None, team2=None, round=1, match_order=1, stage="Main"):
    """Helper to create a match."""
    match = Match(
        category_id=category.id,
        player1_id=player1.id if player1 and not category.is_doubles() else None,
        player2_id=player2.id if player2 and not category.is_doubles() else None,
        team1_id=team1.id if team1 and category.is_doubles() else None,
        team2_id=team2.id if team2 and category.is_doubles() else None,
        round=round,
        match_order=match_order,
        stage=stage,
        is_doubles=category.is_doubles()
    )
    db.session.add(match)
    db.session.commit()
    return match

def create_test_team(db, player1, player2=None):
    """Helper to create a team."""
    team = Team(player1_id=player1.id, player2_id=player2.id if player2 else None)
    db.session.add(team)
    db.session.commit()
    return team

# --- Tests for Update Match ---

def test_update_match_get_as_organizer(client, organizer_user, player_user, test_db):
    """
    GIVEN a Flask app, organizer, players, tournament, category, and match
    WHEN the '/organizer/tournament/<id>/update_match/<match_id>' page is requested (GET)
    THEN check the response is valid and shows match details/score form
    """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)
    category = create_test_category(test_db, tournament, category_type=CategoryType.MENS_SINGLES)
    reg1 = create_test_registration(test_db, player_user, category, seed=1) # Need player_user fixture
    reg2 = create_test_registration(test_db, organizer_user, category, seed=2) # Use organizer as player 2 for simplicity
    match = create_test_match(test_db, category, player1=player_user, player2=organizer_user)

    response = client.get(url_for('organizer.update_match', id=tournament.id, match_id=match.id))

    assert response.status_code == 200
    assert b'Edit Match' in response.data
    assert player_user.username.encode() in response.data
    assert organizer_user.username.encode() in response.data
    assert b'Set 1' in response.data # Check for score fields
    assert b'Court' in response.data
    assert b'Scheduled Time' in response.data
    assert b'Livestream URL' in response.data

def test_update_match_post_update_schedule(client, organizer_user, player_user, test_db, mocker):
    """
    GIVEN a Flask app, organizer, players, tournament, category, and match
    WHEN the update match form is submitted (POST) with changes to court/time/livestream
    THEN check the match details are updated and notifications are potentially triggered
    """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)
    category = create_test_category(test_db, tournament, category_type=CategoryType.MENS_SINGLES)
    reg1 = create_test_registration(test_db, player_user, category, seed=1)
    reg2 = create_test_registration(test_db, organizer_user, category, seed=2)
    match = create_test_match(test_db, category, player1=player_user, player2=organizer_user)

    # Mock the email sending task
    mock_send_email = mocker.patch('app.organizer.match_routes.send_schedule_change_email')
    # Mock socketio emit
    mock_socketio_emit = mocker.patch('app.organizer.match_routes.socketio.emit')


    post_data = {
        'court': 'Court 5',
        'scheduled_time': '14:30:00', # HH:MM:SS format expected by TimeField? Check form field type
        'livestream_url': 'http://newstream.com',
        'set_count': '0', # No scores submitted
        'referee_verified': False,
        'player_verified': False
    }

    response = client.post(url_for('organizer.update_match', id=tournament.id, match_id=match.id), data=post_data, follow_redirects=False)

    assert response.status_code == 302 # Redirects back to update match page
    assert url_for('organizer.update_match', id=tournament.id, match_id=match.id) in response.location

    # Verify DB changes
    test_db.session.refresh(match)
    assert match.court == 'Court 5'
    assert match.scheduled_time == time(14, 30, 0)
    assert match.livestream_url == 'http://newstream.com'

    # Verify notification task was called because schedule changed
    mock_send_email.assert_called_once()
    call_args, _ = mock_send_email.call_args
    assert call_args[0] == match.id # Check match ID passed
    assert 'court' in call_args[1]
    assert 'scheduled_time' in call_args[1]
    assert 'livestream_url' in call_args[1]

    # Verify socketio emit was called for match_update and court_update
    assert mock_socketio_emit.call_count >= 2 # At least match_update and court_update
    # More specific checks on emit calls can be added if needed


def test_update_match_post_update_scores_winner(client, organizer_user, player_user, test_db, mocker):
    """
    GIVEN a Flask app, organizer, players, tournament, category, and match
    WHEN the update match form is submitted (POST) with scores determining a winner
    THEN check scores are saved, winner is set, match completed, and bracket advances
    """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)
    category = create_test_category(test_db, tournament, category_type=CategoryType.MENS_SINGLES)
    reg1 = create_test_registration(test_db, player_user, category, seed=1)
    reg2 = create_test_registration(test_db, organizer_user, category, seed=2)
    match = create_test_match(test_db, category, player1=player_user, player2=organizer_user)

    # Mock BracketService.advance_winner
    mock_advance_winner = mocker.patch('app.organizer.match_routes.BracketService.advance_winner')
    # Mock socketio emit
    mock_socketio_emit = mocker.patch('app.organizer.match_routes.socketio.emit')

    post_data = {
        'court': match.court or '',
        'scheduled_time': match.scheduled_time.strftime('%H:%M:%S') if match.scheduled_time else '',
        'livestream_url': match.livestream_url or '',
        'set_count': '2', # Two sets played
        'scores-0-player1_score': '11',
        'scores-0-player2_score': '5',
        'scores-1-player1_score': '11',
        'scores-1-player2_score': '7',
        'referee_verified': True, # Organizer verifies
        'player_verified': True  # Organizer verifies
    }

    response = client.post(url_for('organizer.update_match', id=tournament.id, match_id=match.id), data=post_data, follow_redirects=False)

    assert response.status_code == 302

    # Verify DB changes
    test_db.session.refresh(match)
    assert match.completed is True
    assert match.winning_player_id == player_user.id # Player 1 won
    assert match.losing_player_id == organizer_user.id
    assert match.referee_verified is True
    assert match.player_verified is True

    # Verify scores were saved
    scores = match.scores.order_by(MatchScore.set_number).all()
    assert len(scores) == 2
    assert scores[0].player1_score == 11
    assert scores[0].player2_score == 5
    assert scores[1].player1_score == 11
    assert scores[1].player2_score == 7

    # Verify bracket advancement was called (if match had a next_match_id)
    if match.next_match_id:
        mock_advance_winner.assert_called_once_with(match)
    else:
        mock_advance_winner.assert_not_called()

    # Verify socketio emit was called
    assert mock_socketio_emit.call_count >= 3 # match_update, score_update, court_update (if court set)


def test_update_match_permission_denied_player(client, player_user, organizer_user, test_db):
    """
    GIVEN a Flask app, organizer, players, tournament, category, and match
    WHEN a player tries to access the organizer's update match page (GET)
    THEN check access is denied
    """
    tournament = create_test_tournament(test_db, organizer_user)
    category = create_test_category(test_db, tournament, category_type=CategoryType.MENS_SINGLES)
    reg1 = create_test_registration(test_db, player_user, category, seed=1)
    reg2 = create_test_registration(test_db, organizer_user, category, seed=2)
    match = create_test_match(test_db, category, player1=player_user, player2=organizer_user)

    # Log in as player
    client.post(url_for('auth.login'), data={'email': player_user.email, 'password': 'password'}, follow_redirects=True)

    response = client.get(url_for('organizer.update_match', id=tournament.id, match_id=match.id), follow_redirects=False)
    assert response.status_code in [302, 403] # Should be forbidden or redirect

# --- Tests for Bracket Generation ---

# Note: Bracket generation logic is complex and likely resides in helpers/services.
# These tests focus on triggering the routes and checking basic outcomes (flash messages, redirects).
# More detailed unit tests should exist for the generation logic itself.

def test_generate_all_brackets_success(client, organizer_user, player_user, test_db):
    """
    GIVEN a Flask app, organizer, tournament with categories and approved registrations
    WHEN the '/organizer/tournament/<id>/generate_all_brackets' route is POSTed to
    THEN check brackets are generated (matches created) and success message is flashed
    """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user, status=TournamentStatus.UPCOMING, format=TournamentFormat.SINGLE_ELIMINATION)
    category1 = create_test_category(test_db, tournament, name="Singles")
    category2 = create_test_category(test_db, tournament, name="Doubles", category_type=CategoryType.MENS_DOUBLES)

    # Add registrations
    create_test_registration(test_db, player_user, category1, seed=1)
    create_test_registration(test_db, organizer_user, category1, seed=2)
    # Add doubles registrations if needed

    initial_match_count = Match.query.count()

    response = client.post(url_for('organizer.generate_all_brackets', id=tournament.id), follow_redirects=True)

    assert response.status_code == 200 # Back to tournament detail page
    assert b'Bracket generation attempted' in response.data
    assert b'succeeded' in response.data # Check for success part of message

    # Verify matches were created
    final_match_count = Match.query.count()
    assert final_match_count > initial_match_count
    assert Match.query.filter_by(category_id=category1.id).count() > 0

def test_generate_all_brackets_wrong_status(client, organizer_user, test_db):
    """
    GIVEN a Flask app, organizer, and an ONGOING tournament
    WHEN the '/organizer/tournament/<id>/generate_all_brackets' route is POSTed to
    THEN check generation is blocked and a warning message is flashed
    """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user, status=TournamentStatus.ONGOING) # Ongoing status

    response = client.post(url_for('organizer.generate_all_brackets', id=tournament.id), follow_redirects=True)

    assert response.status_code == 200
    assert b'Brackets can only be generated for upcoming tournaments.' in response.data

# --- Tests for Calculate Placings ---

# Note: Similar to bracket generation, placing logic is likely in a service.
# Test focuses on route trigger and basic outcome.

def test_calculate_placings_success(client, organizer_user, player_user, test_db, mocker):
    """
    GIVEN a Flask app, organizer, tournament, category with COMPLETED matches
    WHEN the '/organizer/tournament/<id>/calculate_placings/<cat_id>' route is POSTed to
    THEN check PlacingService is called and success message is flashed
    """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user, status=TournamentStatus.COMPLETED)
    category = create_test_category(test_db, tournament, name="Completed Cat")
    reg1 = create_test_registration(test_db, player_user, category, seed=1)
    reg2 = create_test_registration(test_db, organizer_user, category, seed=2)
    match = create_test_match(test_db, category, player1=player_user, player2=organizer_user)
    # Mark match as completed
    match.completed = True
    match.winning_player_id = player_user.id
    test_db.session.commit()

    # Mock the PlacingService methods
    mock_calc_placings = mocker.patch('app.organizer.match_routes.PlacingService.calculate_and_store_placings', return_value=[(1, player_user.id), (2, organizer_user.id)])
    mock_award_points = mocker.patch('app.organizer.match_routes.PlacingService.award_points', return_value=True)

    response = client.post(url_for('organizer.calculate_placings', id=tournament.id, category_id=category.id), follow_redirects=True)

    assert response.status_code == 200 # Back to manage category page
    assert b'Calculated' in response.data
    assert b'placings for category' in response.data
    assert b'Points awarded.' in response.data

    mock_calc_placings.assert_called_once_with(category.id)
    mock_award_points.assert_called_once()

def test_calculate_placings_incomplete_matches(client, organizer_user, player_user, test_db):
    """
    GIVEN a Flask app, organizer, tournament, category with INCOMPLETE matches
    WHEN the '/organizer/tournament/<id>/calculate_placings/<cat_id>' route is POSTed to
    THEN check calculation is blocked and a warning message is flashed
    """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user, status=TournamentStatus.ONGOING)
    category = create_test_category(test_db, tournament, name="Incomplete Cat")
    reg1 = create_test_registration(test_db, player_user, category, seed=1)
    reg2 = create_test_registration(test_db, organizer_user, category, seed=2)
    match = create_test_match(test_db, category, player1=player_user, player2=organizer_user)
    match.completed = False # Match is NOT completed
    test_db.session.commit()

    response = client.post(url_for('organizer.calculate_placings', id=tournament.id, category_id=category.id), follow_redirects=True)

    assert response.status_code == 200
    assert b'Cannot calculate placings:' in response.data
    assert b'matches in this category are not yet completed.' in response.data

# --- Tests for Bulk Edit Matches ---

def test_bulk_edit_matches_get(client, organizer_user, player_user, test_db):
    """ Test GET request for bulk edit matches page """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)
    category = create_test_category(test_db, tournament)
    match1 = create_test_match(test_db, category, player1=player_user, player2=organizer_user, round=1, match_order=1)
    match2 = create_test_match(test_db, category, player1=player_user, player2=organizer_user, round=1, match_order=2) # Dummy match

    response = client.get(url_for('organizer.bulk_edit_matches', id=tournament.id, category_id=category.id))

    assert response.status_code == 200
    assert b'Bulk Edit Matches' in response.data
    assert f'value="{match1.id}"'.encode() in response.data # Check match checkboxes are present
    assert f'value="{match2.id}"'.encode() in response.data
    assert b'Apply to Selected Matches' in response.data

def test_bulk_edit_matches_post_preview(client, organizer_user, player_user, test_db):
    """ Test POST request for bulk edit with 'Preview' action """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)
    category = create_test_category(test_db, tournament)
    match1 = create_test_match(test_db, category, player1=player_user, player2=organizer_user, round=1, match_order=1)
    match2 = create_test_match(test_db, category, player1=player_user, player2=organizer_user, round=1, match_order=2)

    post_data = {
        f'selected_matches-{match1.id}': 'on', # Select match 1
        f'match_ids-{match1.id}': str(match1.id),
        f'selected_matches-{match2.id}': 'on', # Select match 2
        f'match_ids-{match2.id}': str(match2.id),
        'court': 'Court 10',
        'scheduled_date': (datetime.utcnow().date() + timedelta(days=5)).strftime('%Y-%m-%d'),
        'scheduled_time': '10:00:00',
        'preview': 'Preview Changes' # Click the preview button
    }

    response = client.post(url_for('organizer.bulk_edit_matches', id=tournament.id, category_id=category.id), data=post_data)

    assert response.status_code == 200 # Should render confirmation page
    assert b'Confirm Bulk Match Edit' in response.data
    assert b'Court 10' in response.data
    assert b'10:00' in response.data # Check time part
    assert match1.player1.username.encode() in response.data # Check match details are shown
    assert match2.player1.username.encode() in response.data

    # Check session data was stored
    with client.session_transaction() as sess:
        assert 'bulk_edit_data' in sess
        assert sess['bulk_edit_data']['court'] == 'Court 10'
        assert len(sess['bulk_edit_data']['selected_matches']) == 2

def test_confirm_bulk_edit_post(client, organizer_user, player_user, test_db, mocker):
    """ Test POST request to confirm bulk edit """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)
    category = create_test_category(test_db, tournament)
    match1 = create_test_match(test_db, category, player1=player_user, player2=organizer_user, round=1, match_order=1)
    match2 = create_test_match(test_db, category, player1=player_user, player2=organizer_user, round=1, match_order=2)

    # Mock the email sending task
    mock_send_email = mocker.patch('app.organizer.match_routes.send_schedule_change_email')
    # Mock socketio emit
    mock_socketio_emit = mocker.patch('app.organizer.match_routes.socketio.emit')


    # Simulate session data being set by the previous step
    with client.session_transaction() as sess:
        sess['bulk_edit_data'] = {
            'court': 'Court Bulk',
            'scheduled_date': (datetime.utcnow().date() + timedelta(days=6)).isoformat(),
            'scheduled_time': time(11, 0, 0).isoformat(),
            'selected_matches': [match1.id, match2.id]
        }

    response = client.post(url_for('organizer.confirm_bulk_edit', id=tournament.id, category_id=category.id), follow_redirects=False)

    assert response.status_code == 302 # Redirects to manage category page
    assert url_for('organizer.manage_category', id=tournament.id, category_id=category.id) in response.location

    # Verify changes in DB
    test_db.session.refresh(match1)
    test_db.session.refresh(match2)
    expected_dt = datetime.combine(datetime.utcnow().date() + timedelta(days=6), time(11, 0, 0))
    assert match1.court == 'Court Bulk'
    assert match1.scheduled_time == expected_dt
    assert match2.court == 'Court Bulk'
    assert match2.scheduled_time == expected_dt

    # Verify notifications and socket emits were called for each match
    assert mock_send_email.call_count == 2
    assert mock_socketio_emit.call_count >= 4 # match_update + court_update for each match

    # Check session data was cleared
    with client.session_transaction() as sess:
        assert 'bulk_edit_data' not in sess