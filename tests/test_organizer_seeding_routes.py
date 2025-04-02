import pytest
from flask import url_for, json
from app.models import (User, UserRole, Tournament, TournamentCategory, CategoryType,
                        TournamentFormat, Registration, Match)
from tests.test_organizer_tournament_routes import create_test_tournament # Reuse helper
from tests.test_organizer_category_routes import create_test_category # Reuse helper
from tests.test_organizer_match_routes import create_test_registration # Reuse helper

# --- Tests for Manage Seeding Page ---

def test_manage_seeding_get_as_organizer(client, organizer_user, player_user, test_db):
    """
    GIVEN a Flask app, organizer, players, tournament, category, and approved registrations
    WHEN the '/organizer/tournament/<id>/category/<cat_id>/seeding' page is requested (GET)
    THEN check the response is valid and shows registered players for seeding
    """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)
    category = create_test_category(test_db, tournament)
    reg1 = create_test_registration(test_db, player_user, category, seed=1, is_approved=True)
    reg2 = create_test_registration(test_db, organizer_user, category, seed=None, is_approved=True) # Unseeded
    reg_not_approved = create_test_registration(test_db, player_user, category, is_approved=False) # Should not show

    response = client.get(url_for('organizer.manage_seeding', tournament_id=tournament.id, category_id=category.id))

    assert response.status_code == 200
    assert f'Manage Seeding - {category.name}'.encode() in response.data
    assert reg1.team_name.encode() in response.data
    assert b'Seed: 1' in response.data # Check seed is displayed
    assert reg2.team_name.encode() in response.data
    assert b'Unseeded' in response.data # Or however unseeded players are marked
    assert reg_not_approved.team_name.encode() not in response.data # Not approved shouldn't show

def test_manage_seeding_permission_denied_player(client, player_user, organizer_user, test_db):
    """ Test player cannot access the manage seeding page """
    tournament = create_test_tournament(test_db, organizer_user)
    category = create_test_category(test_db, tournament)
    client.post(url_for('auth.login'), data={'email': player_user.email, 'password': 'password'}, follow_redirects=True)

    response = client.get(url_for('organizer.manage_seeding', tournament_id=tournament.id, category_id=category.id), follow_redirects=False)
    assert response.status_code in [302, 403]

def test_manage_seeding_permission_denied_other_organizer(client, organizer_user, other_organizer_user, test_db):
    """ Test organizer cannot access seeding for another organizer's tournament """
    other_tournament = create_test_tournament(test_db, other_organizer_user)
    other_category = create_test_category(test_db, other_tournament)
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)

    response = client.get(url_for('organizer.manage_seeding', tournament_id=other_tournament.id, category_id=other_category.id), follow_redirects=True)
    assert b'You do not have permission to manage seeding for this tournament.' in response.data

# --- Tests for Update Seeding (AJAX) ---

# Note: The route '/tournament/<id>/category/<cat_id>/update_seeds' in match_routes.py seems
# to handle form-based seed updates. The routes in seeding_routes.py seem geared towards AJAX/JSON updates.
# We'll test the AJAX endpoints here.

def test_manage_seeding_post_ajax_update(client, organizer_user, player_user, test_db, mocker):
    """
    GIVEN a Flask app, organizer, players, tournament, category, and registrations
    WHEN the '/organizer/tournament/<id>/category/<cat_id>/seeding' endpoint is POSTed to with JSON data
    THEN check the seeds are updated via the helper function and a JSON success response is returned
    """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)
    category = create_test_category(test_db, tournament)
    reg1 = create_test_registration(test_db, player_user, category, seed=1, is_approved=True)
    reg2 = create_test_registration(test_db, organizer_user, category, seed=2, is_approved=True)

    # Mock the helper function that actually updates seeds
    mock_update_seeds = mocker.patch('app.organizer.seeding_routes.update_match_seeds', return_value=True)

    # Simulate JSON data from a drag-drop or similar UI interaction
    # Format assumes a list of dictionaries: [{'registration_id': id, 'seed': new_seed}, ...]
    new_seed_data = [
        {'registration_id': reg1.id, 'seed': 2}, # Swap seeds
        {'registration_id': reg2.id, 'seed': 1}
    ]

    response = client.post(
        url_for('organizer.manage_seeding', tournament_id=tournament.id, category_id=category.id),
        json=new_seed_data
    )

    assert response.status_code == 200
    assert response.content_type == 'application/json'
    data = json.loads(response.data)
    assert data['success'] is True
    assert 'Seeding updated successfully' in data['message']

    # Verify the helper function was called correctly
    mock_update_seeds.assert_called_once_with(category.id, new_seed_data)

def test_manage_seeding_post_ajax_update_fail(client, organizer_user, player_user, test_db, mocker):
    """
    GIVEN a Flask app and organizer
    WHEN the seeding endpoint is POSTed to with JSON data, but the helper function fails
    THEN check a JSON failure response is returned
    """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)
    category = create_test_category(test_db, tournament)
    reg1 = create_test_registration(test_db, player_user, category, seed=1, is_approved=True)

    # Mock the helper function to return failure
    mock_update_seeds = mocker.patch('app.organizer.seeding_routes.update_match_seeds', return_value=False)

    new_seed_data = [{'registration_id': reg1.id, 'seed': 5}]

    response = client.post(
        url_for('organizer.manage_seeding', tournament_id=tournament.id, category_id=category.id),
        json=new_seed_data
    )

    assert response.status_code == 400 # Bad request due to failed update
    assert response.content_type == 'application/json'
    data = json.loads(response.data)
    assert data['success'] is False
    assert 'Failed to update seeding' in data['message']
    mock_update_seeds.assert_called_once_with(category.id, new_seed_data)


def test_manage_seeding_post_ajax_invalid_data(client, organizer_user, test_db):
    """
    GIVEN a Flask app and organizer
    WHEN the seeding endpoint is POSTed to with invalid JSON data format
    THEN check a JSON failure response is returned
    """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)
    category = create_test_category(test_db, tournament)

    invalid_data = {'registration_id': 1, 'seed': 1} # Not a list as expected by route

    response = client.post(
        url_for('organizer.manage_seeding', tournament_id=tournament.id, category_id=category.id),
        json=invalid_data
    )

    assert response.status_code == 400 # Bad request
    assert response.content_type == 'application/json'
    data = json.loads(response.data)
    assert data['success'] is False
    assert 'Invalid data format' in data['message']


# Test the other AJAX endpoint '/update_seeding' as well, it seems duplicative but might be used differently

def test_update_seeding_ajax_success(client, organizer_user, player_user, test_db, mocker):
    """ Test the '/update_seeding' AJAX endpoint for success """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)
    category = create_test_category(test_db, tournament)
    reg1 = create_test_registration(test_db, player_user, category, seed=1, is_approved=True)
    reg2 = create_test_registration(test_db, organizer_user, category, seed=2, is_approved=True)

    # Mock the helper function
    mock_update_seeds = mocker.patch('app.organizer.seeding_routes.update_match_seeds', return_value=True)

    # Data format expected by this route seems to be {'seeds': {reg_id_str: seed_value, ...}}
    new_seed_data = {
        'seeds': {
            str(reg1.id): 2,
            str(reg2.id): 1
        }
    }

    response = client.post(
        url_for('organizer.update_seeding', id=tournament.id, category_id=category.id),
        json=new_seed_data
    )

    assert response.status_code == 200
    assert response.content_type == 'application/json'
    data = json.loads(response.data)
    assert data['success'] is True
    assert 'Seeds updated successfully' in data['message']

    # Verify helper called with the inner dictionary
    mock_update_seeds.assert_called_once_with(category.id, new_seed_data['seeds'])

def test_update_seeding_ajax_fail(client, organizer_user, player_user, test_db, mocker):
    """ Test the '/update_seeding' AJAX endpoint for failure """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)
    category = create_test_category(test_db, tournament)
    reg1 = create_test_registration(test_db, player_user, category, seed=1, is_approved=True)

    # Mock helper to return failure
    mock_update_seeds = mocker.patch('app.organizer.seeding_routes.update_match_seeds', return_value=False)

    new_seed_data = {'seeds': {str(reg1.id): 5}}

    response = client.post(
        url_for('organizer.update_seeding', id=tournament.id, category_id=category.id),
        json=new_seed_data
    )

    assert response.status_code == 500 # Route returns 500 on helper failure
    assert response.content_type == 'application/json'
    data = json.loads(response.data)
    assert data['success'] is False
    assert 'Failed to update seeds' in data['message']
    mock_update_seeds.assert_called_once_with(category.id, new_seed_data['seeds'])

def test_update_seeding_ajax_permission_denied(client, player_user, organizer_user, test_db):
    """ Test player cannot call the update seeding AJAX endpoint """
    tournament = create_test_tournament(test_db, organizer_user)
    category = create_test_category(test_db, tournament)
    client.post(url_for('auth.login'), data={'email': player_user.email, 'password': 'password'}, follow_redirects=True)

    response = client.post(
        url_for('organizer.update_seeding', id=tournament.id, category_id=category.id),
        json={'seeds': {}}
    )
    assert response.status_code == 403
    data = json.loads(response.data)
    assert data['success'] is False
    assert 'Permission denied' in data['message']