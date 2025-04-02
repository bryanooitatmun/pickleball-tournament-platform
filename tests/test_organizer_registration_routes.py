import pytest
from flask import url_for, json
from app.models import (User, UserRole, Tournament, TournamentCategory, CategoryType,
                        TournamentFormat, Registration, TournamentStatus)
from tests.test_organizer_tournament_routes import create_test_tournament # Reuse helper
from tests.test_organizer_category_routes import create_test_category # Reuse helper
from tests.test_organizer_match_routes import create_test_registration # Reuse helper
from datetime import datetime

# --- Tests for View Registrations (List) ---

def test_view_registrations_get_as_organizer(client, organizer_user, player_user, test_db):
    """
    GIVEN a Flask app, organizer, player, tournament, category, and registrations
    WHEN the '/organizer/registrations' page is requested (GET) by the organizer
    THEN check the response is valid and shows registrations
    """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)
    category = create_test_category(test_db, tournament)
    # Create regs with different statuses
    reg_pending = create_test_registration(test_db, player_user, category, is_approved=False, payment_verified=False)
    reg_pending.payment_status = 'uploaded' # Needs verification
    reg_approved = create_test_registration(test_db, organizer_user, category, is_approved=True, payment_verified=True)
    reg_approved.payment_status = 'paid'
    test_db.session.commit()

    # Default view should show pending
    response = client.get(url_for('organizer.view_registrations'))

    assert response.status_code == 200
    assert b'Tournament Registrations' in response.data
    assert reg_pending.team_name.encode() in response.data # Pending should be visible by default
    assert reg_approved.team_name.encode() not in response.data # Approved shouldn't be in default 'pending' view

def test_view_registrations_filter_status_approved(client, organizer_user, player_user, test_db):
    """ Test filtering registrations by 'approved' status """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)
    category = create_test_category(test_db, tournament)
    reg_pending = create_test_registration(test_db, player_user, category, is_approved=False, payment_verified=False)
    reg_pending.payment_status = 'uploaded'
    reg_approved = create_test_registration(test_db, organizer_user, category, is_approved=True, payment_verified=True)
    reg_approved.payment_status = 'paid'
    test_db.session.commit()

    response = client.get(url_for('organizer.view_registrations', status='approved'))

    assert response.status_code == 200
    assert reg_pending.team_name.encode() not in response.data
    assert reg_approved.team_name.encode() in response.data

def test_view_registrations_filter_status_rejected(client, organizer_user, player_user, test_db):
    """ Test filtering registrations by 'rejected' status """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)
    category = create_test_category(test_db, tournament)
    reg_rejected = create_test_registration(test_db, player_user, category, is_approved=False, payment_verified=False)
    reg_rejected.payment_status = 'rejected'
    reg_approved = create_test_registration(test_db, organizer_user, category, is_approved=True, payment_verified=True)
    reg_approved.payment_status = 'paid'
    test_db.session.commit()

    response = client.get(url_for('organizer.view_registrations', status='rejected'))

    assert response.status_code == 200
    assert reg_rejected.team_name.encode() in response.data
    assert reg_approved.team_name.encode() not in response.data

def test_view_registrations_filter_tournament(client, organizer_user, other_organizer_user, player_user, test_db):
    """ Test filtering registrations by a specific tournament """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament1 = create_test_tournament(test_db, organizer_user, name="Tournament One")
    tournament2 = create_test_tournament(test_db, organizer_user, name="Tournament Two") # Same organizer
    tournament3 = create_test_tournament(test_db, other_organizer_user, name="Other's Tournament") # Different organizer

    category1 = create_test_category(test_db, tournament1)
    category2 = create_test_category(test_db, tournament2)
    category3 = create_test_category(test_db, tournament3)

    reg1 = create_test_registration(test_db, player_user, category1, payment_verified=False) # Belongs to tournament1
    reg1.payment_status = 'uploaded'
    reg2 = create_test_registration(test_db, player_user, category2, payment_verified=False) # Belongs to tournament2
    reg2.payment_status = 'uploaded'
    reg3 = create_test_registration(test_db, player_user, category3, payment_verified=False) # Belongs to tournament3
    reg3.payment_status = 'uploaded'
    test_db.session.commit()

    # Filter for tournament 1
    response = client.get(url_for('organizer.view_registrations', tournament=tournament1.id))
    assert response.status_code == 200
    assert reg1.team_name.encode() in response.data
    assert reg2.team_name.encode() not in response.data
    assert reg3.team_name.encode() not in response.data

    # Filter for tournament 2
    response = client.get(url_for('organizer.view_registrations', tournament=tournament2.id))
    assert response.status_code == 200
    assert reg1.team_name.encode() not in response.data
    assert reg2.team_name.encode() in response.data
    assert reg3.team_name.encode() not in response.data

    # Try to filter for tournament 3 (should not show results as organizer doesn't own it)
    response = client.get(url_for('organizer.view_registrations', tournament=tournament3.id))
    assert response.status_code == 200
    assert reg1.team_name.encode() not in response.data
    assert reg2.team_name.encode() not in response.data
    assert reg3.team_name.encode() not in response.data
    assert b'You do not have permission to view registrations for the selected tournament.' in response.data


def test_view_registrations_permission_denied_player(client, player_user):
    """ Test player cannot access organizer registration list """
    client.post(url_for('auth.login'), data={'email': player_user.email, 'password': 'password'}, follow_redirects=True)
    response = client.get(url_for('organizer.view_registrations'), follow_redirects=False)
    assert response.status_code in [302, 403]

# --- Tests for View Registration (Single) ---

def test_view_registration_get_as_organizer(client, organizer_user, player_user, test_db):
    """ Test organizer can view a specific registration detail """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)
    category = create_test_category(test_db, tournament)
    reg = create_test_registration(test_db, player_user, category)
    reg.payment_proof = 'uploads/proof.jpg' # Simulate uploaded proof
    test_db.session.commit()

    response = client.get(url_for('organizer.view_registration', id=reg.id))

    assert response.status_code == 200
    assert b'View Registration' in response.data
    assert reg.team_name.encode() in response.data
    assert category.name.encode() in response.data
    assert tournament.name.encode() in response.data
    assert b'proof.jpg' in response.data # Check payment proof link/image shown
    assert b'Verify Payment' in response.data # Check action buttons
    assert b'Reject Payment' in response.data

def test_view_registration_permission_denied_other_organizer(client, organizer_user, other_organizer_user, player_user, test_db):
    """ Test organizer cannot view registration from another organizer's tournament """
    # Create registration under other_organizer
    other_tournament = create_test_tournament(test_db, other_organizer_user)
    other_category = create_test_category(test_db, other_tournament)
    other_reg = create_test_registration(test_db, player_user, other_category)

    # Log in as organizer_user
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)

    response = client.get(url_for('organizer.view_registration', id=other_reg.id), follow_redirects=True)
    assert b'You do not have permission to view this registration.' in response.data

# --- Tests for Verify Registration ---

def test_verify_registration_post_success(client, organizer_user, player_user, test_db):
    """ Test successfully verifying a registration payment """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)
    category = create_test_category(test_db, tournament)
    reg = create_test_registration(test_db, player_user, category, is_approved=False, payment_verified=False)
    reg.payment_status = 'uploaded'
    test_db.session.commit()

    assert reg.payment_verified is False
    assert reg.is_approved is False
    assert reg.payment_status == 'uploaded'

    response = client.post(url_for('organizer.verify_registration', id=reg.id), follow_redirects=False)

    assert response.status_code == 302 # Redirects back to view registration page
    assert url_for('organizer.view_registration', id=reg.id) in response.location

    # Verify DB changes
    test_db.session.refresh(reg)
    assert reg.payment_verified is True
    assert reg.is_approved is True
    assert reg.payment_status == 'paid'
    assert reg.payment_verified_by == organizer_user.id
    assert reg.payment_verified_at is not None

def test_verify_registration_permission_denied(client, player_user, organizer_user, test_db):
    """ Test player cannot verify a registration """
    tournament = create_test_tournament(test_db, organizer_user)
    category = create_test_category(test_db, tournament)
    reg = create_test_registration(test_db, player_user, category, is_approved=False, payment_verified=False)

    # Log in as player
    client.post(url_for('auth.login'), data={'email': player_user.email, 'password': 'password'}, follow_redirects=True)

    response = client.post(url_for('organizer.verify_registration', id=reg.id), follow_redirects=True)
    # Depending on decorator, might redirect to login or show error on dashboard
    assert response.status_code == 200 # Or check for specific error message if 403 is used
    assert b'Your account does not have the necessary permissions' in response.data # Check common permission error flash

    # Verify DB state unchanged
    test_db.session.refresh(reg)
    assert reg.payment_verified is False

# --- Tests for Reject Registration ---

def test_reject_registration_post_success(client, organizer_user, player_user, test_db):
    """ Test successfully rejecting a registration payment """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)
    category = create_test_category(test_db, tournament)
    reg = create_test_registration(test_db, player_user, category, is_approved=False, payment_verified=False)
    reg.payment_status = 'uploaded'
    test_db.session.commit()

    rejection_reason = "Payment proof unclear."
    response = client.post(url_for('organizer.reject_registration', id=reg.id), data={'rejection_reason': rejection_reason}, follow_redirects=False)

    assert response.status_code == 302 # Redirects back to view registration page
    assert url_for('organizer.view_registration', id=reg.id) in response.location

    # Verify DB changes
    test_db.session.refresh(reg)
    assert reg.payment_verified is False
    assert reg.is_approved is False
    assert reg.payment_status == 'rejected'
    assert reg.payment_verified_by == organizer_user.id # Tracks who rejected
    assert reg.payment_verified_at is not None
    assert reg.payment_rejection_reason == rejection_reason

# --- Tests for Check-In / Check-Out ---

def test_check_in_player_post_success(client, organizer_user, player_user, test_db, mocker):
    """ Test successfully checking in an approved player """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)
    category = create_test_category(test_db, tournament)
    reg = create_test_registration(test_db, player_user, category, is_approved=True, payment_verified=True) # Must be approved
    test_db.session.commit()

    assert reg.checked_in is False

    # Mock socketio emit
    mock_socketio_emit = mocker.patch('app.organizer.registration_routes.socketio.emit')

    response = client.post(url_for('organizer.check_in_player', id=reg.id), follow_redirects=False)

    assert response.status_code == 302
    assert url_for('organizer.view_registration', id=reg.id) in response.location

    # Verify DB changes
    test_db.session.refresh(reg)
    assert reg.checked_in is True
    assert reg.check_in_time is not None

    # Verify socketio emit
    mock_socketio_emit.assert_called_once_with(
        'player_checked_in',
        mocker.ANY, # Don't need to match exact data structure here unless critical
        room=f'tournament_{tournament.id}'
    )

def test_check_in_player_not_approved(client, organizer_user, player_user, test_db):
    """ Test checking in a player whose registration is not approved """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)
    category = create_test_category(test_db, tournament)
    reg = create_test_registration(test_db, player_user, category, is_approved=False, payment_verified=False) # Not approved
    test_db.session.commit()

    response = client.post(url_for('organizer.check_in_player', id=reg.id), follow_redirects=True) # Follow to check flash

    assert response.status_code == 200 # Back on view registration page
    assert b'Only approved registrations can be checked in.' in response.data

    # Verify DB state unchanged
    test_db.session.refresh(reg)
    assert reg.checked_in is False

def test_check_out_player_post_success(client, organizer_user, player_user, test_db, mocker):
    """ Test successfully checking out a player """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)
    category = create_test_category(test_db, tournament)
    reg = create_test_registration(test_db, player_user, category, is_approved=True, payment_verified=True)
    # Manually check them in first
    reg.checked_in = True
    reg.check_in_time = datetime.utcnow()
    test_db.session.commit()

    assert reg.checked_in is True

    # Mock socketio emit
    mock_socketio_emit = mocker.patch('app.organizer.registration_routes.socketio.emit')

    response = client.post(url_for('organizer.check_out_player', id=reg.id), follow_redirects=False)

    assert response.status_code == 302
    assert url_for('organizer.view_registration', id=reg.id) in response.location

    # Verify DB changes
    test_db.session.refresh(reg)
    assert reg.checked_in is False
    assert reg.check_in_time is None

    # Verify socketio emit
    mock_socketio_emit.assert_called_once_with(
        'player_checked_out',
        mocker.ANY,
        room=f'tournament_{tournament.id}'
    )

# --- Tests for Check-In Status API ---

def test_category_check_in_status_api(client, organizer_user, player_user, test_db):
    """ Test the API endpoint for category check-in status """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)
    category = create_test_category(test_db, tournament)
    reg_checked_in = create_test_registration(test_db, player_user, category, is_approved=True, payment_verified=True)
    reg_checked_in.checked_in = True
    reg_not_checked_in = create_test_registration(test_db, organizer_user, category, is_approved=True, payment_verified=True)
    reg_not_approved = create_test_registration(test_db, player_user, category, is_approved=False, payment_verified=False) # Should not be included
    test_db.session.commit()

    response = client.get(url_for('organizer.category_check_in_status', id=tournament.id, category_id=category.id))

    assert response.status_code == 200
    assert response.content_type == 'application/json'
    data = json.loads(response.data)

    assert data['category_id'] == category.id
    assert data['tournament_id'] == tournament.id
    assert data['total_count'] == 2 # Only approved registrations
    assert data['checked_in_count'] == 1
    assert len(data['registrations']) == 2

    # Check details of one registration
    checked_in_reg_data = next((r for r in data['registrations'] if r['id'] == reg_checked_in.id), None)
    not_checked_in_reg_data = next((r for r in data['registrations'] if r['id'] == reg_not_checked_in.id), None)

    assert checked_in_reg_data is not None
    assert checked_in_reg_data['checked_in'] is True
    assert checked_in_reg_data['check_in_time'] is not None

    assert not_checked_in_reg_data is not None
    assert not_checked_in_reg_data['checked_in'] is False
    assert not_checked_in_reg_data['check_in_time'] is None

def test_category_check_in_status_api_permission_denied(client, player_user, organizer_user, test_db):
    """ Test player cannot access the check-in status API """
    tournament = create_test_tournament(test_db, organizer_user)
    category = create_test_category(test_db, tournament)
    # Log in as player
    client.post(url_for('auth.login'), data={'email': player_user.email, 'password': 'password'}, follow_redirects=True)

    response = client.get(url_for('organizer.category_check_in_status', id=tournament.id, category_id=category.id))
    assert response.status_code == 403 # API should return forbidden
    data = json.loads(response.data)
    assert data['error'] == 'Unauthorized'