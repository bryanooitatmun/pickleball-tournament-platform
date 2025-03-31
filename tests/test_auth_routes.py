import pytest
from flask import url_for, session
from app import db
from app.models import User, UserRole

# Helper function to register a user
def register_user(client, username, email, password):
    return client.post(url_for('auth.register'), data={
        'username': username,
        'email': email,
        'password': password,
        'password2': password # Assuming password confirmation field name
    }, follow_redirects=True)

# Helper function to login a user
def login_user_helper(client, email, password):
     return client.post(url_for('auth.login'), data={
        'email': email,
        'password': password,
        'remember_me': False
    }, follow_redirects=True)

def test_register_route_get(client):
    """Test GET request to the registration page."""
    response = client.get(url_for('auth.register'))
    assert response.status_code == 200
    assert b"Register" in response.data # Check for page title or header

def test_register_route_post_success(client, init_database):
    """Test successful user registration."""
    response = register_user(client, 'testuser', 'test@example.com', 'password123')
    assert response.status_code == 200 # Should redirect to login
    assert b"Sign In" in response.data # Check if redirected to login page
    assert b"Congratulations, you are now a registered player!" in response.data # Check flash message

    # Verify user exists in database
    user = User.query.filter_by(email='test@example.com').first()
    assert user is not None
    assert user.username == 'testuser'
    assert user.role == UserRole.PLAYER
    assert user.check_password('password123')

def test_register_route_post_duplicate_username(client, init_database):
    """Test registration with a duplicate username."""
    # Register first user
    register_user(client, 'testuser', 'test1@example.com', 'password123')
    # Attempt to register second user with same username
    response = register_user(client, 'testuser', 'test2@example.com', 'password456')

    assert response.status_code == 200 # Should re-render registration form
    assert b"Register" in response.data
    assert b"Please use a different username." in response.data # Check form error message

    # Verify only the first user exists
    assert User.query.count() == 1

def test_register_route_post_duplicate_email(client, init_database):
    """Test registration with a duplicate email."""
    # Register first user
    register_user(client, 'user1', 'test@example.com', 'password123')
    # Attempt to register second user with same email
    response = register_user(client, 'user2', 'test@example.com', 'password456')

    assert response.status_code == 200 # Should re-render registration form
    assert b"Register" in response.data
    assert b"Please use a different email address." in response.data # Check form error message

    # Verify only the first user exists
    assert User.query.count() == 1

def test_register_route_already_logged_in(client, init_database):
    """Test accessing register page when already logged in."""
    # Register and log in a user first
    register_user(client, 'testuser', 'test@example.com', 'password123')
    login_user_helper(client, 'test@example.com', 'password123')

    response = client.get(url_for('auth.register'), follow_redirects=True)
    assert response.status_code == 200
    # Should redirect to index (or appropriate dashboard)
    # Check for content expected on the index/dashboard page, not the register page
    assert b"Register" not in response.data
    # Assuming index shows tournament details (based on main routes)
    # Need to create a dummy tournament for index page to render correctly after redirect
    from app.models import Tournament
    from datetime import date, timedelta
    dummy_tournament = Tournament(id=1, name="Dummy", start_date=date.today(), end_date=date.today() + timedelta(days=1))
    db.session.add(dummy_tournament)
    db.session.commit()
    # Re-request after setting up index page dependency
    response = client.get(url_for('auth.register'), follow_redirects=True)
    assert b"Dummy" in response.data # Check for index page content

def test_login_route_get(client):
    """Test GET request to the login page."""
    response = client.get(url_for('auth.login'))
    assert response.status_code == 200
    assert b"Sign In" in response.data

def test_login_route_post_success_player(client, init_database):
    """Test successful login for a player."""
    # Register user first
    register_user(client, 'playeruser', 'player@example.com', 'password123')
    # Attempt login
    response = login_user_helper(client, 'player@example.com', 'password123')
    assert response.status_code == 200
    # Player should be redirected to index by default
    # Check for index page content (requires dummy tournament)
    from app.models import Tournament
    from datetime import date, timedelta
    dummy_tournament = Tournament(id=1, name="Dummy", start_date=date.today(), end_date=date.today() + timedelta(days=1))
    db.session.add(dummy_tournament)
    db.session.commit()
    # Re-request login to ensure redirect target page renders correctly
    response = login_user_helper(client, 'player@example.com', 'password123')
    assert b"Dummy" in response.data
    assert b"Sign In" not in response.data # Should not be on login page

    # Check session state
    with client.session_transaction() as sess:
        assert sess['_user_id'] is not None
        assert sess['_fresh'] is True # Check if session is fresh

def test_login_route_post_success_admin(client, init_database):
    """Test successful login for an admin."""
    # Create admin user directly
    admin_user = User(username='adminuser', email='admin@example.com', role=UserRole.ADMIN)
    admin_user.set_password('adminpass')
    db.session.add(admin_user)
    db.session.commit()
    # Attempt login
    response = login_user_helper(client, 'admin@example.com', 'adminpass')
    assert response.status_code == 200
    # Admin should be redirected to admin dashboard
    # Check for content expected on admin dashboard (adjust based on actual template)
    assert b"Admin Dashboard" in response.data # Example assertion
    assert b"Sign In" not in response.data

def test_login_route_post_incorrect_password(client, init_database):
    """Test login attempt with incorrect password."""
    register_user(client, 'testuser', 'test@example.com', 'password123')
    response = login_user_helper(client, 'test@example.com', 'wrongpassword')
    assert response.status_code == 200 # Should redirect back to login
    assert b"Sign In" in response.data # Still on login page
    assert b"Invalid email or password" in response.data # Check flash message
    # Check session state (should not be logged in)
    with client.session_transaction() as sess:
        assert '_user_id' not in sess

def test_login_route_post_nonexistent_email(client, init_database):
    """Test login attempt with non-existent email."""
    response = login_user_helper(client, 'nosuchuser@example.com', 'password123')
    assert response.status_code == 200 # Should redirect back to login
    assert b"Sign In" in response.data # Still on login page
    assert b"Invalid email or password" in response.data # Check flash message
    # Check session state
    with client.session_transaction() as sess:
        assert '_user_id' not in sess

def test_login_route_already_logged_in(client, init_database):
    """Test accessing login page when already logged in."""
    # Register and log in a user first
    register_user(client, 'testuser', 'test@example.com', 'password123')
    login_user_helper(client, 'test@example.com', 'password123')

    response = client.get(url_for('auth.login'), follow_redirects=True)
    assert response.status_code == 200
    # Should redirect to index (or appropriate dashboard)
    assert b"Sign In" not in response.data
    # Check for index page content (requires dummy tournament)
    from app.models import Tournament
    from datetime import date, timedelta
    dummy_tournament = Tournament(id=1, name="Dummy", start_date=date.today(), end_date=date.today() + timedelta(days=1))
    db.session.add(dummy_tournament)
    db.session.commit()
    # Re-request after setting up index page dependency
    response = client.get(url_for('auth.login'), follow_redirects=True)
    assert b"Dummy" in response.data # Check for index page content

def test_logout_route(client, init_database):
    """Test the logout route."""
    # Register and log in a user first
    register_user(client, 'testuser', 'test@example.com', 'password123')
    login_user_helper(client, 'test@example.com', 'password123')

    # Check user is logged in initially
    with client.session_transaction() as sess:
        assert '_user_id' in sess

    # Perform logout
    response = client.get(url_for('auth.logout'), follow_redirects=True)
    assert response.status_code == 200

    # Check flash message
    assert b"You have been logged out." in response.data

    # Check user is logged out (session cleared)
    with client.session_transaction() as sess:
        assert '_user_id' not in sess
        assert '_fresh' not in sess # Freshness state should also be gone

    # Check redirection target (should be index)
    # Requires dummy tournament for index page
    from app.models import Tournament
    from datetime import date, timedelta
    dummy_tournament = Tournament(id=1, name="Dummy", start_date=date.today(), end_date=date.today() + timedelta(days=1))
    db.session.add(dummy_tournament)
    db.session.commit()
    # Re-request logout to ensure redirect target page renders correctly
    response = client.get(url_for('auth.logout'), follow_redirects=True)
    assert b"Dummy" in response.data # Check for index page content

def test_reset_password_request_route_get(client):
    """Test GET request to the password reset request page."""
    response = client.get(url_for('auth.reset_password_request'))
    assert response.status_code == 200
    assert b"Reset Password" in response.data

def test_reset_password_request_route_post_success(client, init_database):
    """Test successful password reset request."""
    # Register user first
    register_user(client, 'testuser', 'test@example.com', 'password123')
    # Make request
    response = client.post(url_for('auth.reset_password_request'), data={
        'email': 'test@example.com'
    }, follow_redirects=True)
    assert response.status_code == 200 # Should redirect to login
    assert b"Sign In" in response.data
    assert b"Check your email for instructions to reset your password" in response.data # Check flash message

def test_reset_password_request_route_post_nonexistent_email(client, init_database):
    """Test password reset request for a non-existent email."""
    response = client.post(url_for('auth.reset_password_request'), data={
        'email': 'nosuchuser@example.com'
    }, follow_redirects=True)
    assert response.status_code == 200 # Should redirect to login
    assert b"Sign In" in response.data
    # The current implementation flashes the success message even if user doesn't exist
    # This might be desired behaviour to prevent email enumeration, or it might be a bug
    # Test reflects current behaviour:
    assert b"Check your email for instructions to reset your password" in response.data

def test_reset_password_route_get(client):
    """Test GET request to the password reset page (using a dummy token)."""
    # The route requires a token, even if it's not verified yet
    response = client.get(url_for('auth.reset_password', token='dummy_token'))
    assert response.status_code == 200
    assert b"Reset Your Password" in response.data # Check page title/header

def test_reset_password_route_post(client, init_database):
    """Test POST request to the password reset page (using a dummy token)."""
    # Register a user to simulate password reset target (though not actually used by current route)
    register_user(client, 'testuser', 'test@example.com', 'password123')
    # Make request
    response = client.post(url_for('auth.reset_password', token='dummy_token'), data={
        'password': 'newpassword',
        'password2': 'newpassword'
    }, follow_redirects=True)
    assert response.status_code == 200 # Should redirect to login
    assert b"Sign In" in response.data
    assert b"Your password has been reset." in response.data # Check flash message
    # Note: We cannot easily test if the password *actually* changed here
    # because the route logic is currently commented out.