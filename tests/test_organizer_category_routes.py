import pytest
from flask import url_for, json
from app.models import User, UserRole, Tournament, TournamentCategory, CategoryType, TournamentFormat, Registration
from tests.test_organizer_tournament_routes import create_test_tournament # Reuse helper

# --- Helper Functions ---

def create_test_category(db, tournament, name="Test Category", category_type=CategoryType.MENS_SINGLES, max_participants=32, display_order=1):
    """Helper to create a category for testing."""
    category = TournamentCategory(
        tournament_id=tournament.id,
        name=name,
        category_type=category_type,
        max_participants=max_participants,
        points_awarded=100,
        format=tournament.format, # Inherit from tournament by default
        registration_fee=50.0,
        display_order=display_order
    )
    db.session.add(category)
    db.session.commit()
    return category

# --- Tests for Edit Categories (Bulk Editor) ---

def test_edit_categories_get_as_organizer(client, organizer_user, test_db):
    """
    GIVEN a Flask application, an organizer, and a tournament
    WHEN the '/organizer/tournament/<id>/edit/categories' page is requested (GET)
    THEN check the response is valid and shows existing/add category forms
    """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)
    category1 = create_test_category(test_db, tournament, name="Existing Category 1")

    response = client.get(url_for('organizer.edit_categories', id=tournament.id))

    assert response.status_code == 200
    assert f'Edit Categories - {tournament.name}'.encode() in response.data
    assert b'Existing Category 1' in response.data # Check existing category is shown
    assert b'Add New Category' in response.data
    assert b'csrf_token' in response.data

def test_edit_categories_post_add_category(client, organizer_user, test_db):
    """
    GIVEN a Flask application, an organizer, and a tournament
    WHEN the edit categories form is submitted (POST) with data for a new category
    THEN check a new category is created and the user is redirected
    """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)

    post_data = {
        # New category fields (using 'new_' prefix as in the route)
        'new_category_name': ['New Singles Category'],
        'new_category_type': ['MENS_SINGLES'],
        'new_max_participants': ['64'],
        'new_points_awarded': ['150'],
        'new_format': ['SINGLE_ELIMINATION'],
        'new_registration_fee': ['75.00'],
        'new_description': ['A new test category.'],
        'new_display_order': ['1'],
        'new_prize_percentage': [''], # Optional
        'new_prize_money': [''], # Optional
        'new_min_dupr_rating': [''],
        'new_max_dupr_rating': [''],
        'new_min_age': [''],
        'new_max_age': [''],
        'new_gender_restriction': ['']
    }

    response = client.post(url_for('organizer.edit_categories', id=tournament.id), data=post_data, follow_redirects=False)

    # Should redirect to prize editing page after category changes
    assert response.status_code == 302
    assert url_for('organizer.edit_prizes', id=tournament.id) in response.location

    # Verify category was created
    new_category = TournamentCategory.query.filter_by(name='New Singles Category').first()
    assert new_category is not None
    assert new_category.tournament_id == tournament.id
    assert new_category.max_participants == 64
    assert new_category.registration_fee == 75.00
    assert new_category.category_type == CategoryType.MENS_SINGLES

def test_edit_categories_post_update_category(client, organizer_user, test_db):
    """
    GIVEN a Flask application, an organizer, a tournament, and an existing category
    WHEN the edit categories form is submitted (POST) with updated data for the existing category
    THEN check the category is updated in the DB
    """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)
    category = create_test_category(test_db, tournament, name="Old Name", max_participants=16)

    post_data = {
        # Existing category fields (using f'{field}_{category_id}' format)
        'category_id': [str(category.id)],
        f'name_{category.id}': ['Updated Name'],
        f'category_type_{category.id}': [category.category_type.value],
        f'max_participants_{category.id}': ['32'], # Update max participants
        f'points_awarded_{category.id}': [str(category.points_awarded)],
        f'format_{category.id}': [category.format.value],
        f'registration_fee_{category.id}': [str(category.registration_fee)],
        f'description_{category.id}': [category.description or ''],
        f'display_order_{category.id}': [str(category.display_order)],
        f'prize_percentage_{category.id}': [str(category.prize_percentage or '')],
        f'prize_money_{category.id}': [str(category.prize_money or '')],
        f'min_dupr_rating_{category.id}': ['3.0'], # Add restriction
        f'max_dupr_rating_{category.id}': ['4.5'], # Add restriction
        f'min_age_{category.id}': [''],
        f'max_age_{category.id}': [''],
        f'gender_restriction_{category.id}': ['']
    }

    response = client.post(url_for('organizer.edit_categories', id=tournament.id), data=post_data, follow_redirects=False)

    assert response.status_code == 302 # Redirects after successful update

    # Verify category was updated
    test_db.session.refresh(category)
    assert category.name == 'Updated Name'
    assert category.max_participants == 32
    assert category.min_dupr_rating == 3.0
    assert category.max_dupr_rating == 4.5

def test_edit_categories_post_delete_category(client, organizer_user, test_db):
    """
    GIVEN a Flask application, an organizer, a tournament, and an existing category with no registrations
    WHEN the edit categories form is submitted (POST) with the category marked for deletion
    THEN check the category is deleted from the DB
    """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)
    category_to_delete = create_test_category(test_db, tournament, name="Delete Me")
    category_id = category_to_delete.id

    post_data = {
        # Include the ID of the category to delete in the 'delete_category' list
        'delete_category': [str(category_id)]
    }

    response = client.post(url_for('organizer.edit_categories', id=tournament.id), data=post_data, follow_redirects=False)

    assert response.status_code == 302

    # Verify category was deleted
    deleted_category = TournamentCategory.query.get(category_id)
    assert deleted_category is None

def test_edit_categories_post_delete_category_with_registrations(client, organizer_user, player_user, test_db):
    """
    GIVEN a Flask application, an organizer, a tournament, and an existing category WITH registrations
    WHEN the edit categories form is submitted (POST) with the category marked for deletion
    THEN check the category is NOT deleted and a warning flash message is shown
    """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)
    category_to_delete = create_test_category(test_db, tournament, name="Keep Me")
    category_id = category_to_delete.id

    # Add a registration to the category
    reg = Registration(user_id=player_user.id, category_id=category_id, is_approved=True, payment_verified=True)
    test_db.session.add(reg)
    test_db.session.commit()

    post_data = {
        'delete_category': [str(category_id)]
    }

    response = client.post(url_for('organizer.edit_categories', id=tournament.id), data=post_data, follow_redirects=True) # Follow redirect to check flash

    assert response.status_code == 200 # Should redirect back to prize page, then render it
    assert b'Cannot delete category "Keep Me" because it has registrations.' in response.data

    # Verify category was NOT deleted
    kept_category = TournamentCategory.query.get(category_id)
    assert kept_category is not None

def test_edit_categories_permission_denied(client, organizer_user, other_organizer_user, test_db):
    """
    GIVEN a Flask application and two organizers
    WHEN organizer1 tries to access the edit categories page for organizer2's tournament
    THEN check access is denied
    """
    tournament = create_test_tournament(test_db, other_organizer_user)
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)

    response = client.get(url_for('organizer.edit_categories', id=tournament.id), follow_redirects=True)
    assert b'You do not have permission to edit categories for this tournament.' in response.data

# --- Tests for Manage Category (Single Category View/Edit) ---

def test_manage_category_get_as_organizer(client, organizer_user, test_db):
    """
    GIVEN a Flask application, an organizer, a tournament, and a category
    WHEN the '/organizer/tournament/<id>/manage_category/<cat_id>' page is requested (GET)
    THEN check the response is valid and shows category details
    """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)
    category = create_test_category(test_db, tournament, name="Manage Me")

    response = client.get(url_for('organizer.manage_category', id=tournament.id, category_id=category.id))

    assert response.status_code == 200
    assert f'Manage {category.name}'.encode() in response.data
    assert b'Category Settings' in response.data
    assert b'Prize Distribution' in response.data
    assert b'Points Distribution' in response.data
    assert b'Registrations' in response.data
    assert b'Bracket / Matches' in response.data

def test_manage_category_post_update_settings(client, organizer_user, test_db):
    """
    GIVEN a Flask application, an organizer, a tournament, and a category
    WHEN the manage category form is submitted (POST) with action 'update_settings'
    THEN check the category settings are updated
    """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user, format=TournamentFormat.GROUP_KNOCKOUT)
    category = create_test_category(test_db, tournament, name="Settings Update", max_participants=16)

    post_data = {
        'action': 'update_settings',
        'max_participants': '24', # Update
        'points_awarded': '120', # Update
        'prize_percentage': '80.0', # Update
        'min_dupr_rating': '3.5', # Add
        'max_dupr_rating': '',
        'min_age': '',
        'max_age': '',
        'gender_restriction': 'MALE', # Add
        'group_count': '8', # Update group setting
        'teams_advancing_per_group': '1' # Update group setting
    }

    response = client.post(url_for('organizer.manage_category', id=tournament.id, category_id=category.id), data=post_data, follow_redirects=False)

    assert response.status_code == 302 # Redirects back to same page
    assert url_for('organizer.manage_category', id=tournament.id, category_id=category.id) in response.location

    # Verify updates
    test_db.session.refresh(category)
    assert category.max_participants == 24
    assert category.points_awarded == 120
    assert category.prize_percentage == 80.0
    assert category.min_dupr_rating == 3.5
    assert category.gender_restriction == 'MALE'
    assert category.group_count == 8
    assert category.teams_advancing_per_group == 1

def test_manage_category_post_update_prize_distribution(client, organizer_user, test_db):
    """
    GIVEN a Flask application, an organizer, a tournament, and a category
    WHEN the manage category form is submitted (POST) with action 'update_prize_distribution'
    THEN check the category prize_distribution JSON is updated
    """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)
    category = create_test_category(test_db, tournament, name="Prize Distro")

    post_data = {
        'action': 'update_prize_distribution',
        'prize_1': '50', # 1st place gets 50%
        'prize_2': '30', # 2nd place gets 30%
        'prize_3-4': '10' # 3rd/4th place each get 10% (assuming key format)
        # 'prize_5-8': '' # Left blank
    }

    response = client.post(url_for('organizer.manage_category', id=tournament.id, category_id=category.id), data=post_data, follow_redirects=False)

    assert response.status_code == 302

    # Verify update
    test_db.session.refresh(category)
    assert category.prize_distribution is not None
    assert category.prize_distribution.get('1') == 50.0
    assert category.prize_distribution.get('2') == 30.0
    assert category.prize_distribution.get('3-4') == 10.0
    assert '5-8' not in category.prize_distribution

def test_manage_category_post_update_points_distribution(client, organizer_user, test_db):
    """
    GIVEN a Flask application, an organizer, a tournament, and a category
    WHEN the manage category form is submitted (POST) with action 'update_points_distribution'
    THEN check the category points_distribution JSON is updated
    """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)
    category = create_test_category(test_db, tournament, name="Points Distro")

    post_data = {
        'action': 'update_points_distribution',
        'points_1': '100',
        'points_2': '70',
        'points_3-4': '50',
        'points_5-8': '30'
    }

    response = client.post(url_for('organizer.manage_category', id=tournament.id, category_id=category.id), data=post_data, follow_redirects=False)

    assert response.status_code == 302

    # Verify update
    test_db.session.refresh(category)
    assert category.points_distribution is not None
    assert category.points_distribution.get('1') == 100.0
    assert category.points_distribution.get('5-8') == 30.0

# Add tests for bracket generation POST actions ('generate_bracket')
# Add tests for permission denied scenarios on manage_category