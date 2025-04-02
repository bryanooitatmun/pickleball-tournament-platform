import pytest
from flask import url_for
from app.models import User, UserRole, Tournament, TournamentStatus
from datetime import datetime, timedelta

# Sample data creation helpers (consider moving to conftest.py if reused)
def create_test_tournament(db, organizer, name="Test Tournament", status=TournamentStatus.UPCOMING, days_offset=10):
    """Helper to create a tournament for testing."""
    start_date = datetime.utcnow().date() + timedelta(days=days_offset)
    end_date = start_date + timedelta(days=2)
    tournament = Tournament(
        name=name,
        organizer_id=organizer.id,
        start_date=start_date,
        end_date=end_date,
        location="Test Location",
        description="A test tournament.",
        status=status
    )
    db.session.add(tournament)
    db.session.commit()
    return tournament

# --- Tests for Organizer Dashboard ---

def test_organizer_dashboard_get_as_organizer(client, organizer_user, test_db):
    """
    GIVEN a Flask application configured for testing and an organizer user
    WHEN the '/organizer/dashboard' page is requested (GET) by the logged-in organizer
    THEN check that the response is valid and contains expected content
    """
    # Log in as the organizer
    client.post(url_for('auth.login'), data={
        'email': organizer_user.email,
        'password': 'password' # Assuming default password from fixtures
    }, follow_redirects=True)

    # Create a sample tournament for this organizer to display
    create_test_tournament(test_db, organizer_user, name="Organizer's Upcoming Tourney")

    # Make GET request to the dashboard
    response = client.get(url_for('organizer.dashboard'))

    # Assertions
    assert response.status_code == 200
    assert b'Organizer Dashboard' in response.data
    assert b"Organizer's Upcoming Tourney" in response.data # Check if tournament is listed
    assert b'Upcoming Tournaments' in response.data
    assert b'Ongoing Tournaments' in response.data
    assert b'Completed Tournaments' in response.data

def test_organizer_dashboard_get_as_admin(client, admin_user, organizer_user, test_db):
    """
    GIVEN a Flask application configured for testing and an admin user
    WHEN the '/organizer/dashboard' page is requested (GET) by the logged-in admin
    THEN check that the response is valid and shows tournaments from other organizers
    """
    # Log in as the admin
    client.post(url_for('auth.login'), data={
        'email': admin_user.email,
        'password': 'password'
    }, follow_redirects=True)

    # Create tournaments for both admin (as organizer) and another organizer
    create_test_tournament(test_db, admin_user, name="Admin's Own Tourney")
    create_test_tournament(test_db, organizer_user, name="Other Organizer's Tourney")

    response = client.get(url_for('organizer.dashboard'))

    assert response.status_code == 200
    assert b'Organizer Dashboard' in response.data
    assert b"Admin's Own Tourney" in response.data
    assert b"Other Organizer's Tourney" in response.data # Admin should see all

def test_organizer_dashboard_get_as_player(client, player_user):
    """
    GIVEN a Flask application configured for testing and a player user
    WHEN the '/organizer/dashboard' page is requested (GET) by the logged-in player
    THEN check that access is forbidden (redirects to login or shows error)
    """
    client.post(url_for('auth.login'), data={
        'email': player_user.email,
        'password': 'password'
    }, follow_redirects=True)

    response = client.get(url_for('organizer.dashboard'), follow_redirects=False) # Don't follow redirects to check status

    # Expecting a redirect (302) or forbidden (403) depending on decorator/login_manager behavior
    assert response.status_code in [302, 403]
    # If redirect, check it goes somewhere sensible (like main index or player dashboard)
    if response.status_code == 302:
         assert url_for('main.index') in response.location or url_for('player.dashboard') in response.location

def test_organizer_dashboard_get_unauthenticated(client):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/organizer/dashboard' page is requested (GET) without authentication
    THEN check that the user is redirected to the login page
    """
    response = client.get(url_for('organizer.dashboard'), follow_redirects=False)
    assert response.status_code == 302 # Should redirect to login
    assert url_for('auth.login') in response.location

# --- Tests for Create Tournament ---

def test_create_tournament_get_as_organizer(client, organizer_user):
    """
    GIVEN a Flask application and a logged-in organizer user
    WHEN the '/organizer/tournament/create' page is requested (GET)
    THEN check the response is valid and the form is present
    """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    response = client.get(url_for('organizer.create_tournament'))
    assert response.status_code == 200
    assert b'Create Tournament' in response.data
    assert b'Tournament Name' in response.data # Check for a form field label
    assert b'csrf_token' in response.data # Check for CSRF token

def test_create_tournament_post_success(client, organizer_user, test_db):
    """
    GIVEN a Flask application and a logged-in organizer user
    WHEN the '/organizer/tournament/create' page is submitted (POST) with valid data
    THEN check a new Tournament is created and the user is redirected
    """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)

    start_date = (datetime.utcnow() + timedelta(days=30)).strftime('%Y-%m-%d')
    end_date = (datetime.utcnow() + timedelta(days=32)).strftime('%Y-%m-%d')

    tournament_data = {
        'name': 'My New Awesome Tournament',
        'start_date': start_date,
        'end_date': end_date,
        'location': 'Online',
        'description': 'The best tournament ever.',
        'tier': 'REGIONAL', # Assuming REGIONAL is a valid TournamentTier enum value
        'format': 'SINGLE_ELIMINATION', # Assuming SINGLE_ELIMINATION is valid
        'status': 'UPCOMING', # Assuming UPCOMING is valid
        'prize_pool': '1000.00',
        # Add other required fields if any (logo, banner might need file handling tests)
        'payment_bank_name': 'Test Bank',
        'payment_account_name': 'Test Account',
        'payment_account_number': '1234567890',
        'door_gifts_description': 'Cool stuff'
    }

    response = client.post(url_for('organizer.create_tournament'), data=tournament_data, follow_redirects=False) # Don't follow redirect yet

    # Check for redirect to category editing page
    assert response.status_code == 302
    assert '/edit/categories' in response.location # Check redirect URL part

    # Verify tournament was created in DB
    tournament = Tournament.query.filter_by(name='My New Awesome Tournament').first()
    assert tournament is not None
    assert tournament.organizer_id == organizer_user.id
    assert tournament.location == 'Online'
    assert tournament.tier.name == 'REGIONAL'
    assert tournament.format.name == 'SINGLE_ELIMINATION'
    assert tournament.status.name == 'UPCOMING'
    assert tournament.prize_pool == 1000.00

def test_create_tournament_post_invalid_data(client, organizer_user):
    """
    GIVEN a Flask application and a logged-in organizer user
    WHEN the '/organizer/tournament/create' page is submitted (POST) with invalid data (e.g., missing name)
    THEN check the form is re-rendered with errors and no tournament is created
    """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)

    start_date = (datetime.utcnow() + timedelta(days=30)).strftime('%Y-%m-%d')
    end_date = (datetime.utcnow() + timedelta(days=32)).strftime('%Y-%m-%d')

    tournament_data = {
        'name': '', # Missing name
        'start_date': start_date,
        'end_date': end_date,
        'location': 'Online',
        'description': 'The best tournament ever.',
        'tier': 'REGIONAL',
        'format': 'SINGLE_ELIMINATION',
        'status': 'UPCOMING',
    }

    response = client.post(url_for('organizer.create_tournament'), data=tournament_data, follow_redirects=True)

    assert response.status_code == 200 # Should re-render the form page
    assert b'Create Tournament' in response.data
    assert b'This field is required.' in response.data # Check for WTForms error message
    assert Tournament.query.filter_by(location='Online').first() is None # Ensure no tournament was created

# --- Tests for Edit Tournament ---

def test_edit_tournament_get(client, organizer_user, test_db):
    """
    GIVEN a Flask application, an organizer, and an existing tournament
    WHEN the '/organizer/tournament/<id>/edit' page is requested (GET)
    THEN check the response is valid and the form is pre-filled
    """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user, name="Tournament To Edit", status=TournamentStatus.UPCOMING)

    response = client.get(url_for('organizer.edit_tournament', id=tournament.id))

    assert response.status_code == 200
    assert b'Edit Tournament - Tournament To Edit' in response.data
    assert b'value="Tournament To Edit"' in response.data # Check name is pre-filled
    assert b'value="Test Location"' in response.data # Check location is pre-filled
    assert b'<option value="UPCOMING" selected>' in response.data # Check status dropdown selection

def test_edit_tournament_post_success(client, organizer_user, test_db):
    """
    GIVEN a Flask application, an organizer, and an existing tournament
    WHEN the '/organizer/tournament/<id>/edit' page is submitted (POST) with valid changes
    THEN check the tournament is updated in the DB and the user is redirected
    """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user, name="Original Name", status=TournamentStatus.UPCOMING)

    start_date = (datetime.utcnow() + timedelta(days=40)).strftime('%Y-%m-%d')
    end_date = (datetime.utcnow() + timedelta(days=42)).strftime('%Y-%m-%d')

    edit_data = {
        'name': 'Updated Tournament Name',
        'start_date': start_date,
        'end_date': end_date,
        'location': 'Updated Location',
        'description': tournament.description, # Keep original
        'tier': tournament.tier.name if tournament.tier else '',
        'format': tournament.format.name if tournament.format else '',
        'status': TournamentStatus.ONGOING.name, # Change status
        'prize_pool': '2500.50',
        'payment_bank_name': 'Updated Bank',
        'payment_account_name': 'Updated Account',
        'payment_account_number': '9876543210',
        'door_gifts_description': 'Updated Gifts'
    }

    response = client.post(url_for('organizer.edit_tournament', id=tournament.id), data=edit_data, follow_redirects=False)

    assert response.status_code == 302 # Should redirect back to edit page (or detail)
    assert url_for('organizer.edit_tournament', id=tournament.id) in response.location

    # Verify changes in DB
    db.session.refresh(tournament) # Refresh object from DB
    assert tournament.name == 'Updated Tournament Name'
    assert tournament.location == 'Updated Location'
    assert tournament.status == TournamentStatus.ONGOING
    assert tournament.prize_pool == 2500.50
    assert tournament.payment_bank_name == 'Updated Bank'

def test_edit_tournament_permission_denied(client, organizer_user, other_organizer_user, test_db):
    """
    GIVEN a Flask application and two organizers
    WHEN organizer1 tries to edit organizer2's tournament
    THEN check access is denied (redirect + flash message)
    """
    # Create tournament for other_organizer_user
    tournament = create_test_tournament(test_db, other_organizer_user, name="Other User's Tournament")

    # Log in as organizer_user
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)

    # Attempt to access edit page for the other user's tournament
    response_get = client.get(url_for('organizer.edit_tournament', id=tournament.id))
    assert response_get.status_code == 302 # Should redirect
    assert url_for('organizer.tournament_detail', id=tournament.id) in response_get.location # Redirects to detail page

    # Check for flash message after redirect
    response_redirect = client.get(response_get.location)
    assert b'You do not have permission to edit this tournament.' in response_redirect.data

    # Attempt to POST to the edit page
    response_post = client.post(url_for('organizer.edit_tournament', id=tournament.id), data={'name': 'Hacked Name'}, follow_redirects=True)
    assert b'You do not have permission to edit this tournament.' in response_post.data
    db.session.refresh(tournament)
    assert tournament.name == "Other User's Tournament" # Name should not have changed

# --- Tests for Payment Settings ---

def test_payment_settings_get(client, organizer_user, test_db):
    """ Test GET request for payment settings page """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user, name="Payment Test Tourney")
    tournament.payment_bank_name = "Initial Bank"
    db.session.commit()

    response = client.get(url_for('organizer.payment_settings', id=tournament.id))
    assert response.status_code == 200
    assert b'Payment Settings' in response.data
    assert b'value="Initial Bank"' in response.data

def test_payment_settings_post(client, organizer_user, test_db):
    """ Test POST request to update payment settings """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user, name="Payment Update Tourney")

    payment_data = {
        'payment_bank_name': 'New Bank Name',
        'payment_account_name': 'New Account Name',
        'payment_account_number': '1122334455',
        'payment_instructions': 'Pay here please.'
    }
    response = client.post(url_for('organizer.payment_settings', id=tournament.id), data=payment_data, follow_redirects=False)

    assert response.status_code == 302
    assert url_for('organizer.tournament_detail', id=tournament.id) in response.location

    db.session.refresh(tournament)
    assert tournament.payment_bank_name == 'New Bank Name'
    assert tournament.payment_account_number == '1122334455'
    assert tournament.payment_instructions == 'Pay here please.'

# --- Tests for Door Gifts ---

def test_door_gifts_get(client, organizer_user, test_db):
    """ Test GET request for door gifts page """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user, name="Gifts Test Tourney")
    tournament.door_gifts_description = "Initial Gifts"
    db.session.commit()

    response = client.get(url_for('organizer.door_gifts', id=tournament.id))
    assert response.status_code == 200
    assert b'Door Gifts' in response.data
    assert b'Initial Gifts' in response.data # Check description is pre-filled in textarea

def test_door_gifts_post(client, organizer_user, test_db):
    """ Test POST request to update door gifts """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user, name="Gifts Update Tourney")

    gifts_data = {
        'door_gifts_description': 'Updated awesome door gifts!',
        'door_gifts_pickup_info': 'Collect at registration desk.'
    }
    response = client.post(url_for('organizer.door_gifts', id=tournament.id), data=gifts_data, follow_redirects=False)

    assert response.status_code == 302
    assert url_for('organizer.tournament_detail', id=tournament.id) in response.location

    db.session.refresh(tournament)
    assert tournament.door_gifts_description == 'Updated awesome door gifts!'
    assert tournament.door_gifts_pickup_info == 'Collect at registration desk.'

# --- Tests for Payment Dashboard ---

def test_payment_dashboard_get(client, organizer_user, test_db):
    """ Test GET request for the payment dashboard """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    # Add some data (tournaments, categories, registrations with different statuses) later if needed for content checks
    response = client.get(url_for('organizer.payment_dashboard'))
    assert response.status_code == 200
    assert b'Payment Dashboard' in response.data
    assert b'Pending Verification' in response.data
    assert b'Approved Payments' in response.data
    assert b'Total Revenue by Tournament' in response.data

# Add more tests for edge cases, file uploads, different user roles accessing pages, etc.