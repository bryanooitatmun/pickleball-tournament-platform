import pytest
from flask import url_for, session
from app import db
from app.models import User, PlayerProfile, UserRole
from werkzeug.datastructures import FileStorage
import os
from unittest.mock import patch # For mocking file saving

# --- Reusable Helper Functions (Copied from dashboard tests - consider refactoring) ---

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

# --- Test Cases for create_profile ---

def test_create_profile_access_denied_not_logged_in(client):
    """Test accessing /player/create_profile without being logged in."""
    response = client.get(url_for('player.create_profile'), follow_redirects=False)
    assert response.status_code == 302
    assert url_for('auth.login') in response.location

def test_create_profile_get(client, init_database):
    """Test GET request to the create_profile page."""
    register_test_user(client, 'createuser', 'create@test.com', 'password123')
    login_test_user(client, 'create@test.com', 'password123')

    response = client.get(url_for('player.create_profile'))
    assert response.status_code == 200
    assert b"Create Player Profile" in response.data
    # Check if form fields are present
    assert b"full_name" in response.data
    assert b"bio" in response.data

@patch('app.helpers.registration.save_picture') # Mock the save_picture helper
def test_create_profile_post_success(mock_save_picture, client, init_database):
    """Test successful profile creation via POST request."""
    # Mock save_picture to return a dummy filename without actually saving
    mock_save_picture.side_effect = lambda file, folder: f"{folder}/{file.filename}"

    register_test_user(client, 'createuser', 'create@test.com', 'password123')
    login_test_user(client, 'create@test.com', 'password123')
    user = User.query.filter_by(email='create@test.com').first()

    # Simulate file uploads (optional, testing without files first)
    data = {
        'full_name': 'Test Creator',
        'bio': 'My awesome bio.',
        'phone_number': '1234567890',
        'gender': 'Male',
        'birth_date': '2000-01-01',
        # Add other form fields as needed
    }
    # Example with file upload simulation:
    # data['profile_image'] = (FileStorage(filename='test.jpg', content_type='image/jpeg'), 'test.jpg')

    response = client.post(url_for('player.create_profile'), data=data, content_type='multipart/form-data', follow_redirects=True)

    assert response.status_code == 200
    # Should redirect to dashboard
    assert b"Player Dashboard" in response.data
    assert b"Your player profile has been created!" in response.data # Check flash message

    # Verify profile exists in database
    profile = PlayerProfile.query.filter_by(user_id=user.id).first()
    assert profile is not None
    assert profile.full_name == 'Test Creator'
    assert profile.bio == 'My awesome bio.'
    assert profile.phone_number == '1234567890'
    # assert profile.profile_image == 'profile_pics/test.jpg' # If file upload was tested

def test_create_profile_redirects_if_profile_exists(client, init_database):
    """Test accessing create_profile redirects to edit_profile if profile exists."""
    register_test_user(client, 'existinguser', 'existing@test.com', 'password123')
    login_test_user(client, 'existing@test.com', 'password123')
    user = User.query.filter_by(email='existing@test.com').first()

    # Create a profile manually first
    existing_profile = PlayerProfile(user_id=user.id, full_name="Already Here")
    db.session.add(existing_profile)
    db.session.commit()

    response = client.get(url_for('player.create_profile'), follow_redirects=False)
    assert response.status_code == 302
    assert url_for('player.edit_profile') in response.location

    # Check flash message after redirect
    response_redirected = client.get(url_for('player.create_profile'), follow_redirects=True)
    assert b"Edit Player Profile" in response_redirected.data # Should show edit page
    assert b"You already have a player profile." in response_redirected.data

# --- Test Cases for edit_profile ---

def test_edit_profile_access_denied_not_logged_in(client):
    """Test accessing /player/edit_profile without being logged in."""
    response = client.get(url_for('player.edit_profile'), follow_redirects=False)
    assert response.status_code == 302
    assert url_for('auth.login') in response.location

def test_edit_profile_404_if_no_profile(client, init_database):
    """Test accessing edit_profile returns 404 if user has no profile."""
    register_test_user(client, 'edituser_noprofile', 'edit_np@test.com', 'password123')
    login_test_user(client, 'edit_np@test.com', 'password123')

    response = client.get(url_for('player.edit_profile'))
    assert response.status_code == 404 # Should be 404 as per first_or_404()

def test_edit_profile_get(client, init_database):
    """Test GET request to the edit_profile page shows pre-filled form."""
    register_test_user(client, 'edituser', 'edit@test.com', 'password123')
    login_test_user(client, 'edit@test.com', 'password123')
    user = User.query.filter_by(email='edit@test.com').first()

    # Create a profile first
    profile = PlayerProfile(user_id=user.id, full_name="Initial Name", bio="Initial Bio")
    db.session.add(profile)
    db.session.commit()

    response = client.get(url_for('player.edit_profile'))
    assert response.status_code == 200
    assert b"Edit Player Profile" in response.data
    # Check if form fields are pre-filled
    assert b'value="Initial Name"' in response.data
    assert b"Initial Bio</textarea>" in response.data # Check textarea content

@patch('app.helpers.registration.save_picture') # Mock the save_picture helper
def test_edit_profile_post_success(mock_save_picture, client, init_database):
    """Test successful profile update via POST request."""
    mock_save_picture.side_effect = lambda file, folder: f"{folder}/{file.filename}"

    register_test_user(client, 'edituser', 'edit@test.com', 'password123')
    login_test_user(client, 'edit@test.com', 'password123')
    user = User.query.filter_by(email='edit@test.com').first()

    # Create initial profile
    profile = PlayerProfile(user_id=user.id, full_name="Initial Name", bio="Initial Bio")
    db.session.add(profile)
    db.session.commit()

    # Data for update
    data = {
        'full_name': 'Updated Name',
        'bio': 'Updated Bio.',
        'phone_number': '9876543210',
        'gender': 'Female',
        'birth_date': '1999-12-12',
        # Add other fields
    }
    # Simulate file upload for update
    # data['action_image'] = (FileStorage(filename='action.png', content_type='image/png'), 'action.png')

    response = client.post(url_for('player.edit_profile'), data=data, content_type='multipart/form-data', follow_redirects=True)

    assert response.status_code == 200
    # Should redirect to dashboard
    assert b"Player Dashboard" in response.data
    assert b"Your player profile has been updated!" in response.data # Check flash message

    # Verify profile is updated in database
    db.session.refresh(profile) # Refresh object from session/DB
    assert profile.full_name == 'Updated Name'
    assert profile.bio == 'Updated Bio.'
    assert profile.phone_number == '9876543210'
    # assert profile.action_image == 'action_pics/action.png' # If file upload tested

# --- Test Cases for change_password ---

def test_change_password_access_denied_not_logged_in(client):
    """Test accessing /player/change_password without being logged in."""
    response = client.get(url_for('player.change_password'), follow_redirects=False)
    assert response.status_code == 302
    assert url_for('auth.login') in response.location

def test_change_password_get(client, init_database):
    """Test GET request to the change_password page."""
    register_test_user(client, 'passuser', 'pass@test.com', 'oldpassword')
    login_test_user(client, 'pass@test.com', 'oldpassword')

    response = client.get(url_for('player.change_password'))
    assert response.status_code == 200
    assert b"Change Password" in response.data
    assert b"current_password" in response.data
    assert b"new_password" in response.data
    assert b"confirm_new_password" in response.data # Assuming form field name

def test_change_password_post_success(client, init_database):
    """Test successful password change via POST request."""
    register_test_user(client, 'passuser', 'pass@test.com', 'oldpassword')
    login_test_user(client, 'pass@test.com', 'oldpassword')
    user = User.query.filter_by(email='pass@test.com').first()

    response = client.post(url_for('player.change_password'), data={
        'current_password': 'oldpassword',
        'new_password': 'newpassword',
        'confirm_new_password': 'newpassword'
    }, follow_redirects=True)

    assert response.status_code == 200
    # Should redirect to dashboard
    assert b"Player Dashboard" in response.data
    assert b"Your password has been updated!" in response.data # Check flash message

    # Verify password was actually changed
    db.session.refresh(user)
    assert user.check_password('newpassword')
    assert not user.check_password('oldpassword')

def test_change_password_post_incorrect_current(client, init_database):
    """Test password change fails with incorrect current password."""
    register_test_user(client, 'passuser', 'pass@test.com', 'oldpassword')
    login_test_user(client, 'pass@test.com', 'oldpassword')
    user = User.query.filter_by(email='pass@test.com').first()

    response = client.post(url_for('player.change_password'), data={
        'current_password': 'wrongpassword',
        'new_password': 'newpassword',
        'confirm_new_password': 'newpassword'
    }, follow_redirects=True)

    assert response.status_code == 200
    # Should re-render change password form
    assert b"Change Password" in response.data
    assert b"Current password is incorrect." in response.data # Check flash message

    # Verify password was NOT changed
    db.session.refresh(user)
    assert user.check_password('oldpassword')
    assert not user.check_password('newpassword')

def test_change_password_post_mismatch_new(client, init_database):
    """Test password change fails if new passwords don't match."""
    register_test_user(client, 'passuser', 'pass@test.com', 'oldpassword')
    login_test_user(client, 'pass@test.com', 'oldpassword')
    user = User.query.filter_by(email='pass@test.com').first()

    response = client.post(url_for('player.change_password'), data={
        'current_password': 'oldpassword',
        'new_password': 'newpassword1',
        'confirm_new_password': 'newpassword2' # Mismatch
    }, follow_redirects=True)

    assert response.status_code == 200
    # Should re-render change password form
    assert b"Change Password" in response.data
    assert b"Field must be equal to new_password." in response.data # Check form validation error

    # Verify password was NOT changed
    db.session.refresh(user)
    assert user.check_password('oldpassword')