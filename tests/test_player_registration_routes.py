import pytest
from flask import url_for, session, jsonify
from app import db
from app.models import User, PlayerProfile, UserRole, Tournament, TournamentStatus, TournamentCategory, Registration, CategoryType
from datetime import date, timedelta, datetime
from unittest.mock import patch

# --- Reusable Helper Functions (Consider refactoring to conftest) ---

def register_test_user(client, username, email, password, ic_number=None):
    """Registers a basic player user."""
    data = {
        'username': username,
        'email': email,
        'password': password,
        'password2': password
    }
    # Note: Registration form might not include IC, profile form does.
    # We might need to create user directly or update profile later for IC tests.
    return client.post(url_for('auth.register'), data=data, follow_redirects=True)

def login_test_user(client, email, password):
    """Logs in a user."""
    return client.post(url_for('auth.login'), data={
        'email': email,
        'password': password,
        'remember_me': False
    }, follow_redirects=True)

def create_test_profile(user_id, full_name="Test Player", country="Testland", phone="123", dob=None, ic_number=None, dupr_id=None):
    """Creates a player profile directly in DB."""
    profile = PlayerProfile(
        user_id=user_id,
        full_name=full_name,
        country=country,
        date_of_birth=dob or date(2000, 1, 1),
        dupr_id=dupr_id
        # Add other fields if needed by form prefill
    )
    # Update user phone/ic if provided
    user = User.query.get(user_id)
    if phone: user.phone = phone
    if ic_number: user.ic_number = ic_number
    db.session.add(profile)
    db.session.add(user) # Add user too if updated
    db.session.commit()
    return profile

def create_test_tournament(id, name, status=TournamentStatus.UPCOMING, reg_deadline_days_offset=5, start_days_offset=10, end_days_offset=12):
    """Creates a test tournament."""
    today = date.today()
    tournament = Tournament(
        id=id,
        name=name,
        status=status,
        registration_deadline=today + timedelta(days=reg_deadline_days_offset),
        start_date=today + timedelta(days=start_days_offset),
        end_date=today + timedelta(days=end_days_offset)
    )
    db.session.add(tournament)
    db.session.commit()
    return tournament

def create_test_category(id, tournament_id, name="Test Singles", category_type=CategoryType.MENS_SINGLES, fee=10.0, max_participants=16, display_order=1):
    """Creates a test tournament category."""
    category = TournamentCategory(
        id=id,
        tournament_id=tournament_id,
        name=name,
        category_type=category_type,
        registration_fee=fee,
        max_participants=max_participants,
        display_order=display_order
    )
    db.session.add(category)
    db.session.commit()
    return category

# --- Test Cases for /register_tournament/<id> ---

def test_register_tournament_get_not_logged_in(client, init_database):
    """Test GET request to registration page when not logged in."""
    tournament = create_test_tournament(1, "Open Reg Tournament")
    create_test_category(1, tournament.id)
    response = client.get(url_for('player.register_tournament', tournament_id=tournament.id))
    assert response.status_code == 200
    assert b"Register for Open Reg Tournament" in response.data # Check title/header
    assert b"Player 1 Information" in response.data
    # Check that player 1 fields are empty (not pre-filled)
    assert b'name="player1_name" type="text" value=""' in response.data

def test_register_tournament_get_logged_in(client, init_database):
    """Test GET request pre-fills form when logged in."""
    register_test_user(client, 'reguser', 'reg@test.com', 'password123')
    login_test_user(client, 'reg@test.com', 'password123')
    user = User.query.filter_by(email='reg@test.com').first()
    create_test_profile(user.id, full_name="Reg User", country="Regland", phone="5551234", dob=date(1995, 5, 5), ic_number="IC123", dupr_id="D123")

    tournament = create_test_tournament(1, "Open Reg Tournament")
    create_test_category(1, tournament.id)

    response = client.get(url_for('player.register_tournament', tournament_id=tournament.id))
    assert response.status_code == 200
    assert b"Register for Open Reg Tournament" in response.data
    # Check that player 1 fields are pre-filled
    assert b'name="player1_name" type="text" value="Reg User"' in response.data
    assert b'name="player1_email" type="email" value="reg@test.com"' in response.data
    assert b'name="player1_phone" type="text" value="5551234"' in response.data
    assert b'name="player1_nationality" type="text" value="Regland"' in response.data
    assert b'name="player1_date_of_birth" type="date" value="1995-05-05"' in response.data
    assert b'name="player1_ic_number" type="text" value="IC123"' in response.data
    assert b'name="player1_dupr_id" type="text" value="D123"' in response.data

def test_register_tournament_closed(client, init_database):
    """Test accessing registration for a closed tournament."""
    tournament = create_test_tournament(1, "Closed Reg Tournament", reg_deadline_days_offset=-1) # Deadline passed
    response = client.get(url_for('player.register_tournament', tournament_id=tournament.id), follow_redirects=True)
    assert response.status_code == 200
    assert b"Registration for this tournament is closed." in response.data
    assert url_for('main.tournament_detail', id=tournament.id) in request.url # Check redirect target

@patch('app.player.registration_routes.generate_payment_reference') # Mock helper
def test_register_tournament_post_success_singles_logged_in(mock_gen_ref, client, init_database):
    """Test successful POST for singles registration (logged in)."""
    mock_gen_ref.return_value = "TESTREF123"
    register_test_user(client, 'reguser', 'reg@test.com', 'password123')
    login_test_user(client, 'reg@test.com', 'password123')
    user = User.query.filter_by(email='reg@test.com').first()
    create_test_profile(user.id, full_name="Reg User", ic_number="IC123") # Need profile

    tournament = create_test_tournament(1, "Single Reg Open")
    category = create_test_category(1, tournament.id, name="Men's Singles", fee=20.0)

    data = {
        'category_id': category.id,
        # Player 1 details are pre-filled for logged-in user, not needed in POST unless overriding
        # We need the agreement checkboxes
        'terms_agreement': 'y',
        'liability_waiver': 'y',
        'media_release': 'y',
        'pdpa_consent': 'y',
        # Other fields like special requests if needed
    }

    response = client.post(url_for('player.register_tournament', tournament_id=tournament.id), data=data, follow_redirects=False) # Don't follow redirect yet

    # Verify Registration created
    reg = Registration.query.filter_by(category_id=category.id).first()
    assert reg is not None
    assert reg.player_id == user.player_profile.id
    assert reg.partner_id is None
    assert reg.is_team_registration is False
    assert reg.registration_fee == 20.0
    assert reg.payment_reference == "TESTREF123"
    assert reg.payment_status == 'pending' # Default status
    assert reg.payment_verified is False
    assert reg.terms_agreement is True

    # Check redirection to payment page
    assert response.status_code == 302
    assert url_for('player.payment', registration_id=reg.id) in response.location

@patch('app.player.registration_routes.generate_payment_reference')
def test_register_tournament_post_success_singles_free(mock_gen_ref, client, init_database):
    """Test successful POST for singles registration with zero fee."""
    mock_gen_ref.return_value = "FREEREF456"
    register_test_user(client, 'freeuser', 'free@test.com', 'password123')
    login_test_user(client, 'free@test.com', 'password123')
    user = User.query.filter_by(email='free@test.com').first()
    create_test_profile(user.id, full_name="Free User")

    tournament = create_test_tournament(1, "Free Reg Open")
    category = create_test_category(1, tournament.id, name="Free Singles", fee=0.0) # Zero fee

    data = {
        'category_id': category.id,
        'terms_agreement': 'y', 'liability_waiver': 'y', 'media_release': 'y', 'pdpa_consent': 'y',
    }

    response = client.post(url_for('player.register_tournament', tournament_id=tournament.id), data=data, follow_redirects=False)

    # Verify Registration created and auto-approved
    reg = Registration.query.filter_by(category_id=category.id).first()
    assert reg is not None
    assert reg.player_id == user.player_profile.id
    assert reg.payment_status == 'free'
    assert reg.payment_verified is True
    assert reg.is_approved is True
    assert reg.payment_verified_at is not None

    # Check redirection to confirmation page
    assert response.status_code == 302
    assert url_for('player.registration_confirmation', registration_id=reg.id) in response.location

    # Check flash message after redirect
    response_redirected = client.post(url_for('player.register_tournament', tournament_id=tournament.id), data=data, follow_redirects=True)
    assert b'Registration successful! No payment required.' in response_redirected.data

@patch('app.player.registration_routes.generate_payment_reference')
def test_register_tournament_post_success_doubles_anon_partner(mock_gen_ref, client, init_database):
    """Test successful POST for doubles registration (logged in, anonymous partner)."""
    mock_gen_ref.return_value = "DOUBLESREF789"
    register_test_user(client, 'player1_doubles', 'p1d@test.com', 'password123')
    login_test_user(client, 'p1d@test.com', 'password123')
    user1 = User.query.filter_by(email='p1d@test.com').first()
    profile1 = create_test_profile(user1.id, full_name="Player One Doubles")

    tournament = create_test_tournament(1, "Doubles Reg Open")
    category = create_test_category(1, tournament.id, name="Men's Doubles", category_type=CategoryType.MENS_DOUBLES, fee=30.0)

    data = {
        'category_id': category.id,
        # Player 1 details pre-filled
        # Player 2 details (anonymous partner)
        'player2_name': 'Anonymous Partner',
        'player2_email': 'anon_partner@test.com',
        'player2_email_confirm': 'anon_partner@test.com',
        'player2_phone': '1112223333',
        'player2_nationality': 'Partnerland',
        'player2_date_of_birth': '1998-02-02',
        'player2_ic_number': 'ICPARTNER',
        'player2_dupr_id': 'DPARTNER',
        # Agreements
        'terms_agreement': 'y', 'liability_waiver': 'y', 'media_release': 'y', 'pdpa_consent': 'y',
    }

    response = client.post(url_for('player.register_tournament', tournament_id=tournament.id), data=data, follow_redirects=False)

    # Verify Registration created
    reg = Registration.query.filter_by(category_id=category.id).first()
    assert reg is not None
    assert reg.player_id == profile1.id # Logged-in user is player 1
    assert reg.partner_id is None # Partner is anonymous for now
    assert reg.is_team_registration is True
    assert reg.registration_fee == 30.0
    assert reg.payment_reference == "DOUBLESREF789"
    assert reg.payment_status == 'pending'
    # Check anonymous partner details stored
    assert reg.player2_name == 'Anonymous Partner'
    assert reg.player2_email == 'anon_partner@test.com'
    assert reg.player2_ic_number == 'ICPARTNER'

    # Check redirection to payment page
    assert response.status_code == 302
    assert url_for('player.payment', registration_id=reg.id) in response.location

@patch('app.player.registration_routes.generate_payment_reference')
def test_register_tournament_post_success_doubles_found_partner(mock_gen_ref, client, init_database):
    """Test successful POST for doubles registration (logged in, partner found via IC)."""
    mock_gen_ref.return_value = "FOUNDPARTNER111"
    # Create Player 1
    register_test_user(client, 'player1_found', 'p1f@test.com', 'password123')
    login_test_user(client, 'p1f@test.com', 'password123') # Login as Player 1
    user1 = User.query.filter_by(email='p1f@test.com').first()
    profile1 = create_test_profile(user1.id, full_name="Player One Found", ic_number="ICP1F")

    # Create Player 2 (Partner) - needs user and profile with IC
    user2 = User(username='player2_partner', email='p2partner@test.com', ic_number="ICP2PARTNER")
    user2.set_password('partnerpass') # Need password if they were to login
    db.session.add(user2)
    db.session.commit() # Commit user before creating profile
    profile2 = create_test_profile(user2.id, full_name="Partner Found", ic_number="ICP2PARTNER")

    tournament = create_test_tournament(1, "Found Partner Doubles")
    category = create_test_category(1, tournament.id, name="Mixed Doubles", category_type=CategoryType.MIXED_DOUBLES, fee=40.0)

    data = {
        'category_id': category.id,
        # Player 1 details pre-filled
        # Player 2 details - Simulate finding partner via IC and submitting profile ID
        'player2_profile_id': profile2.id, # This hidden field is key
        # Agreements
        'terms_agreement': 'y', 'liability_waiver': 'y', 'media_release': 'y', 'pdpa_consent': 'y',
    }

    response = client.post(url_for('player.register_tournament', tournament_id=tournament.id), data=data, follow_redirects=False)

    # Verify Registration created
    reg = Registration.query.filter_by(category_id=category.id).first()
    assert reg is not None
    assert reg.player_id == profile1.id # Logged-in user is player 1
    assert reg.partner_id == profile2.id # Partner ID linked correctly
    assert reg.is_team_registration is True
    assert reg.registration_fee == 40.0
    assert reg.payment_reference == "FOUNDPARTNER111"
    assert reg.payment_status == 'pending'
    # Check anonymous partner details are NOT stored
    assert reg.player2_name is None
    assert reg.player2_email is None

    # Check redirection to payment page
    assert response.status_code == 302
    assert url_for('player.payment', registration_id=reg.id) in response.location

def test_register_tournament_post_fail_category_full(client, init_database):
    """Test registration fails if the category is full."""
    register_test_user(client, 'player_full', 'p_full@test.com', 'password123')
    login_test_user(client, 'p_full@test.com', 'password123')
    user = User.query.filter_by(email='p_full@test.com').first()
    create_test_profile(user.id, full_name="Player Full")

    tournament = create_test_tournament(1, "Full Category Open")
    # Category with max 1 participant
    category = create_test_category(1, tournament.id, name="Limited Singles", fee=10.0, max_participants=1)

    # Create one existing *verified* registration to fill the spot
    existing_user = User(username='existing', email='exist@test.com')
    db.session.add(existing_user)
    db.session.commit()
    existing_profile = create_test_profile(existing_user.id, full_name="Existing Player")
    existing_reg = Registration(
        category_id=category.id,
        player_id=existing_profile.id,
        payment_status='paid',
        payment_verified=True, # Mark as verified to count towards capacity
        is_approved=True
    )
    db.session.add(existing_reg)
    db.session.commit()

    data = {
        'category_id': category.id,
        'terms_agreement': 'y', 'liability_waiver': 'y', 'media_release': 'y', 'pdpa_consent': 'y',
    }

    response = client.post(url_for('player.register_tournament', tournament_id=tournament.id), data=data, follow_redirects=True)

    assert response.status_code == 200 # Should re-render form
    assert b'Register for Full Category Open' in response.data
    assert f'Sorry, the category "{category.name}" is full'.encode('utf-8') in response.data # Check flash message
    # Verify no new registration was created for the current user
    assert Registration.query.filter_by(player_id=user.player_profile.id).count() == 0

def test_register_tournament_post_fail_already_registered(client, init_database):
    """Test registration fails if the player is already registered."""
    register_test_user(client, 'player_dup', 'p_dup@test.com', 'password123')
    login_test_user(client, 'p_dup@test.com', 'password123')
    user = User.query.filter_by(email='p_dup@test.com').first()
    create_test_profile(user.id, full_name="Player Duplicate")

    tournament = create_test_tournament(1, "Duplicate Reg Open")
    category = create_test_category(1, tournament.id, name="Singles Dup", fee=10.0)

    # Create an initial registration for this player
    initial_reg = Registration(category_id=category.id, player_id=user.player_profile.id)
    db.session.add(initial_reg)
    db.session.commit()

    data = {
        'category_id': category.id,
        'terms_agreement': 'y', 'liability_waiver': 'y', 'media_release': 'y', 'pdpa_consent': 'y',
    }

    response = client.post(url_for('player.register_tournament', tournament_id=tournament.id), data=data, follow_redirects=True)

    assert response.status_code == 200 # Should re-render form
    assert b'Register for Duplicate Reg Open' in response.data
    assert b'You (Player 1) are already registered for this category.' in response.data # Check flash message
    # Verify only one registration exists
    assert Registration.query.filter_by(player_id=user.player_profile.id).count() == 1

# --- Test Cases for /find_user_by_ic ---

def test_find_user_by_ic_success(client, init_database):
    """Test finding a user by IC number successfully."""
    # Create a user with an IC number and profile
    user_to_find = User(username='findme', email='findme@test.com', ic_number='ICFINDME')
    db.session.add(user_to_find)
    db.session.commit()
    profile_to_find = create_test_profile(user_to_find.id, full_name="Find Me Player", ic_number='ICFINDME', dupr_id='DFINDME')

    response = client.post(url_for('player.find_user_by_ic'), data={'ic_number': 'ICFINDME'})
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['success'] is True
    assert json_data['message'] == 'User found'
    assert json_data['user']['profile_id'] == profile_to_find.id
    assert json_data['user']['name'] == 'Find Me Player'
    assert json_data['user']['email'] == 'findme@test.com'
    assert json_data['user']['dupr_id'] == 'DFINDME'

def test_find_user_by_ic_not_found(client, init_database):
    """Test finding a user with a non-existent IC number."""
    response = client.post(url_for('player.find_user_by_ic'), data={'ic_number': 'ICNOTFOUND'})
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['success'] is False
    assert json_data['message'] == 'No user found with this IC number'

def test_find_user_by_ic_no_ic_provided(client, init_database):
    """Test the endpoint when no IC number is provided."""
    response = client.post(url_for('player.find_user_by_ic'), data={})
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['success'] is False
    assert json_data['message'] == 'No IC number provided'

def test_find_user_by_ic_finds_self(client, init_database):
    """Test finding the logged-in user's own IC number."""
    register_test_user(client, 'selfuser', 'self@test.com', 'password123')
    login_test_user(client, 'self@test.com', 'password123')
    user = User.query.filter_by(email='self@test.com').first()
    # Update user IC directly for test simplicity
    user.ic_number = 'ICSELF'
    db.session.add(user)
    db.session.commit()
    create_test_profile(user.id, full_name="Self User", ic_number='ICSELF')

    response = client.post(url_for('player.find_user_by_ic'), data={'ic_number': 'ICSELF'})
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['success'] is False
    assert 'This is your own IC number.' in json_data['message']

def test_find_user_by_ic_user_no_profile(client, init_database):
    """Test finding a user who exists but has no player profile."""
    user_no_profile = User(username='no_profile_user', email='np@test.com', ic_number='ICNOPROFILE')
    db.session.add(user_no_profile)
    db.session.commit()

    response = client.post(url_for('player.find_user_by_ic'), data={'ic_number': 'ICNOPROFILE'})
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['success'] is False
    assert 'User found, but player profile is incomplete.' in json_data['message']

# --- Test Cases for /payment/<id> ---

def test_payment_route_get(client, init_database):
    """Test GET request to the payment page."""
    # Setup: Register a user and create a pending registration
    register_test_user(client, 'payuser', 'pay@test.com', 'password123')
    login_test_user(client, 'pay@test.com', 'password123')
    user = User.query.filter_by(email='pay@test.com').first()
    profile = create_test_profile(user.id, full_name="Pay User")
    tournament = create_test_tournament(1, "Payment Tournament")
    category = create_test_category(1, tournament.id, fee=50.0)
    reg = Registration(category_id=category.id, player_id=profile.id, registration_fee=50.0, payment_reference="PAYREF1")
    db.session.add(reg)
    db.session.commit()

    response = client.get(url_for('player.payment', registration_id=reg.id))
    assert response.status_code == 200
    assert b"Complete Your Registration Payment" in response.data
    assert b"Tournament: Payment Tournament" in response.data
    assert b"Amount Due: $50.00" in response.data # Check fee display
    assert b"Payment Reference: PAYREF1" in response.data
    assert b"Upload Payment Proof" in response.data
    assert b'name="payment_proof"' in response.data # Check file input

@patch('app.player.registration_routes.save_payment_proof') # Mock file saving
@patch('app.models.registration.Registration.create_user_accounts') # Mock account creation/email
def test_payment_route_post_success(mock_create_accounts, mock_save_proof, client, init_database):
    """Test successful payment proof upload."""
    mock_save_proof.return_value = "uploads/payment_proofs/proof_1.jpg" # Simulate saved path
    mock_create_accounts.return_value = None # Don't need return value

    # Setup: Register user, create pending registration
    register_test_user(client, 'payuser', 'pay@test.com', 'password123')
    login_test_user(client, 'pay@test.com', 'password123')
    user = User.query.filter_by(email='pay@test.com').first()
    profile = create_test_profile(user.id, full_name="Pay User")
    tournament = create_test_tournament(1, "Payment Tournament")
    category = create_test_category(1, tournament.id, fee=50.0)
    reg = Registration(category_id=category.id, player_id=profile.id, registration_fee=50.0, payment_reference="PAYREF2")
    db.session.add(reg)
    db.session.commit()

    # Simulate file upload
    from io import BytesIO
    data = {
        'payment_proof': (BytesIO(b"dummy proof data"), 'proof.jpg')
    }

    response = client.post(url_for('player.payment', registration_id=reg.id), data=data, content_type='multipart/form-data', follow_redirects=False) # Don't follow redirect

    # Verify registration updated
    db.session.refresh(reg)
    assert reg.payment_status == 'uploaded'
    assert reg.payment_proof == "uploads/payment_proofs/proof_1.jpg"
    assert reg.payment_proof_uploaded_at is not None
    mock_save_proof.assert_called_once() # Check helper was called
    mock_create_accounts.assert_called_once() # Check account creation was triggered

    # Check redirection to confirmation page
    assert response.status_code == 302
    assert url_for('player.registration_confirmation', registration_id=reg.id) in response.location

    # Check flash message after redirect
    response_redirected = client.post(url_for('player.payment', registration_id=reg.id), data=data, content_type='multipart/form-data', follow_redirects=True)
    assert b'Payment proof uploaded. Registration pending verification.' in response_redirected.data

def test_payment_route_already_verified(client, init_database):
    """Test accessing payment page for an already verified registration."""
    # Setup: Register user, create verified registration
    register_test_user(client, 'payuser', 'pay@test.com', 'password123')
    login_test_user(client, 'pay@test.com', 'password123')
    user = User.query.filter_by(email='pay@test.com').first()
    profile = create_test_profile(user.id, full_name="Pay User")
    tournament = create_test_tournament(1, "Payment Tournament")
    category = create_test_category(1, tournament.id, fee=50.0)
    reg = Registration(
        category_id=category.id,
        player_id=profile.id,
        registration_fee=50.0,
        payment_reference="PAYREF3",
        payment_status='paid',
        payment_verified=True, # Already verified
        is_approved=True
    )
    db.session.add(reg)
    db.session.commit()

    response = client.get(url_for('player.payment', registration_id=reg.id), follow_redirects=False) # Don't follow redirect

    # Check redirection to confirmation page
    assert response.status_code == 302
    assert url_for('player.registration_confirmation', registration_id=reg.id) in response.location

    # Check flash message after redirect
    response_redirected = client.get(url_for('player.payment', registration_id=reg.id), follow_redirects=True)
    assert b'This registration has already been paid and verified.' in response_redirected.data
    assert b'Registration Confirmation' in response_redirected.data # Check confirmation page content


# --- Test Cases for /registration_confirmation/<id> ---

def test_confirmation_route_pending(client, init_database):
    """Test confirmation page for a pending (uploaded proof) registration."""
    # Setup: Register user, create pending registration
    register_test_user(client, 'confuser', 'conf@test.com', 'password123')
    # No need to login, confirmation page should be public
    user = User.query.filter_by(email='conf@test.com').first()
    profile = create_test_profile(user.id, full_name="Conf User")
    tournament = create_test_tournament(1, "Confirm Tournament")
    category = create_test_category(1, tournament.id, fee=50.0)
    reg = Registration(
        category_id=category.id,
        player_id=profile.id,
        registration_fee=50.0,
        payment_reference="CONFREF1",
        payment_status='uploaded', # Proof uploaded, pending verification
        payment_proof='uploads/proof.jpg'
    )
    db.session.add(reg)
    db.session.commit()

    response = client.get(url_for('player.registration_confirmation', registration_id=reg.id))
    assert response.status_code == 200
    assert b"Registration Confirmation" in response.data
    assert b"Confirm Tournament" in response.data
    assert b"Status: Pending Verification" in response.data # Check status display
    assert b"Payment Reference: CONFREF1" in response.data

def test_confirmation_route_verified(client, init_database):
    """Test confirmation page for a verified registration."""
    # Setup: Register user, create verified registration
    register_test_user(client, 'confuser', 'conf@test.com', 'password123')
    user = User.query.filter_by(email='conf@test.com').first()
    profile = create_test_profile(user.id, full_name="Conf User")
    tournament = create_test_tournament(1, "Confirm Tournament")
    category = create_test_category(1, tournament.id, fee=50.0)
    reg = Registration(
        category_id=category.id,
        player_id=profile.id,
        registration_fee=50.0,
        payment_reference="CONFREF2",
        payment_status='paid',
        payment_verified=True, # Verified
        is_approved=True
    )
    db.session.add(reg)
    db.session.commit()

    response = client.get(url_for('player.registration_confirmation', registration_id=reg.id))
    assert response.status_code == 200
    assert b"Registration Confirmation" in response.data
    assert b"Status: Confirmed" in response.data # Check status display

def test_confirmation_route_rejected(client, init_database):
    """Test confirmation page for a rejected registration."""
    # Setup: Register user, create rejected registration
    register_test_user(client, 'confuser', 'conf@test.com', 'password123')
    user = User.query.filter_by(email='conf@test.com').first()
    profile = create_test_profile(user.id, full_name="Conf User")
    tournament = create_test_tournament(1, "Confirm Tournament")
    category = create_test_category(1, tournament.id, fee=50.0)
    reg = Registration(
        category_id=category.id,
        player_id=profile.id,
        registration_fee=50.0,
        payment_reference="CONFREF3",
        payment_status='rejected', # Rejected
        payment_verified=False,
        is_approved=False
    )
    db.session.add(reg)
    db.session.commit()

    response = client.get(url_for('player.registration_confirmation', registration_id=reg.id))
    assert response.status_code == 200
    assert b"Registration Confirmation" in response.data
    assert b"Status: Payment Rejected" in response.data # Check status display

def test_confirmation_route_free(client, init_database):
    """Test confirmation page for a free registration."""
    # Setup: Register user, create free registration
    register_test_user(client, 'confuser', 'conf@test.com', 'password123')
    user = User.query.filter_by(email='conf@test.com').first()
    profile = create_test_profile(user.id, full_name="Conf User")
    tournament = create_test_tournament(1, "Confirm Tournament")
    category = create_test_category(1, tournament.id, fee=0.0) # Free
    reg = Registration(
        category_id=category.id,
        player_id=profile.id,
        registration_fee=0.0,
        payment_reference="CONFREF4",
        payment_status='free', # Free
        payment_verified=True,
        is_approved=True
    )
    db.session.add(reg)
    db.session.commit()

    response = client.get(url_for('player.registration_confirmation', registration_id=reg.id))
    assert response.status_code == 200
    assert b"Registration Confirmation" in response.data
    # Template might need adjustment for free status display
    assert b"Status: Confirmed" in response.data or b"Status: Confirmed (Free)" in response.data

def test_confirmation_route_not_found(client, init_database):
    """Test accessing confirmation for a non-existent registration."""
    response = client.get(url_for('player.registration_confirmation', registration_id=999))
    assert response.status_code == 404

# --- Test Cases for /my_registrations ---

def test_my_registrations_access_denied_not_logged_in(client):
    """Test accessing /my_registrations without being logged in."""
    response = client.get(url_for('player.my_registrations'), follow_redirects=False)
    assert response.status_code == 302
    assert url_for('auth.login') in response.location

def test_my_registrations_redirect_to_create_profile(client, init_database):
    """Test accessing my_registrations redirects if user has no profile."""
    register_test_user(client, 'myreg_np', 'myreg_np@test.com', 'password123')
    login_test_user(client, 'myreg_np@test.com', 'password123')

    response = client.get(url_for('player.my_registrations'), follow_redirects=False)
    assert response.status_code == 302
    assert url_for('player.create_profile') in response.location

    # Check flash message after redirect
    response_redirected = client.get(url_for('player.my_registrations'), follow_redirects=True)
    assert b"Please create your player profile to view registrations." in response_redirected.data
    assert b"Create Player Profile" in response_redirected.data # Check redirect target content

def test_my_registrations_no_registrations(client, init_database):
    """Test my_registrations page when user has a profile but no registrations."""
    register_test_user(client, 'myreg_empty', 'myreg_e@test.com', 'password123')
    login_test_user(client, 'myreg_e@test.com', 'password123')
    user = User.query.filter_by(email='myreg_e@test.com').first()
    create_test_profile(user.id, full_name="MyReg Empty")

    response = client.get(url_for('player.my_registrations'))
    assert response.status_code == 200
    assert b"My Tournament Registrations" in response.data
    # Check for a message indicating no registrations (adjust based on template)
    assert b"You have no tournament registrations yet." in response.data

def test_my_registrations_with_data(client, init_database):
    """Test my_registrations page displays various registrations correctly."""
    # Setup User 1 (logged in)
    register_test_user(client, 'myreg_user', 'myreg@test.com', 'password123')
    login_test_user(client, 'myreg@test.com', 'password123')
    user1 = User.query.filter_by(email='myreg@test.com').first()
    profile1 = create_test_profile(user1.id, full_name="MyReg User")

    # Setup User 2 (partner)
    user2 = User(username='myreg_partner', email='myreg_p@test.com')
    db.session.add(user2)
    db.session.commit()
    profile2 = create_test_profile(user2.id, full_name="MyReg Partner")

    # Setup Tournaments and Categories
    t1 = create_test_tournament(1, "MyReg Tourney 1", start_days_offset=10)
    t2 = create_test_tournament(2, "MyReg Tourney 2", start_days_offset=5) # Earlier start date
    cat1_t1 = create_test_category(1, t1.id, name="T1 Singles", fee=10.0)
    cat2_t1 = create_test_category(2, t1.id, name="T1 Doubles", category_type=CategoryType.MENS_DOUBLES, fee=20.0)
    cat1_t2 = create_test_category(3, t2.id, name="T2 Mixed", category_type=CategoryType.MIXED_DOUBLES, fee=30.0)

    # Create Registrations
    # 1. User 1 in T1 Singles
    reg1 = Registration(category_id=cat1_t1.id, player_id=profile1.id, payment_status='paid', payment_verified=True)
    # 2. User 1 + User 2 in T1 Doubles
    reg2 = Registration(category_id=cat2_t1.id, player_id=profile1.id, partner_id=profile2.id, payment_status='uploaded')
    # 3. User 2 + User 1 in T2 Mixed (User 1 is partner)
    reg3 = Registration(category_id=cat1_t2.id, player_id=profile2.id, partner_id=profile1.id, payment_status='rejected')
    db.session.add_all([reg1, reg2, reg3])
    db.session.commit()

    response = client.get(url_for('player.my_registrations'))
    assert response.status_code == 200
    assert b"My Tournament Registrations" in response.data

    # Check tournaments are displayed (sorted by start date desc: T1 then T2)
    assert response.data.find(b"MyReg Tourney 1") < response.data.find(b"MyReg Tourney 2")

    # Check categories within tournaments
    assert b"T1 Singles" in response.data
    assert b"T1 Doubles" in response.data
    assert b"T2 Mixed" in response.data

    # Check registration statuses are displayed (adjust based on template)
    assert b"Status: Confirmed" in response.data # For reg1
    assert b"Status: Pending Verification" in response.data # For reg2
    assert b"Status: Payment Rejected" in response.data # For reg3

    # Check partner name is displayed where applicable
    assert b"Partner: MyReg Partner" in response.data # For reg2
    # Check player name is displayed when logged-in user is partner
    assert b"Player: MyReg Partner" in response.data or b"Registered with: MyReg Partner" in response.data # For reg3


# --- Test Cases for /cancel_registration/<id> ---

def test_cancel_registration_success(client, init_database):
    """Test successful registration cancellation."""
    # Setup user and registration
    register_test_user(client, 'canceluser', 'cancel@test.com', 'password123')
    login_test_user(client, 'cancel@test.com', 'password123')
    user = User.query.filter_by(email='cancel@test.com').first()
    profile = create_test_profile(user.id, full_name="Cancel User")
    tournament = create_test_tournament(1, "Cancel Tourney", status=TournamentStatus.UPCOMING)
    category = create_test_category(1, tournament.id, fee=10.0)
    reg = Registration(
        category_id=category.id,
        player_id=profile.id,
        payment_status='pending' # Not paid yet
    )
    db.session.add(reg)
    db.session.commit()
    reg_id = reg.id # Store ID before potential deletion

    # Perform cancellation
    response = client.post(url_for('player.cancel_registration', registration_id=reg_id), follow_redirects=True)

    assert response.status_code == 200
    assert b"My Tournament Registrations" in response.data # Should redirect back to list
    assert b"Your tournament registration has been cancelled." in response.data # Check flash message

    # Verify registration is deleted
    assert Registration.query.get(reg_id) is None

def test_cancel_registration_fail_not_logged_in(client, init_database):
    """Test cancelling registration fails if not logged in."""
    # Setup registration without logging in user
    user = User(username='canceluser', email='cancel@test.com')
    db.session.add(user)
    db.session.commit()
    profile = create_test_profile(user.id)
    tournament = create_test_tournament(1, "Cancel Tourney")
    category = create_test_category(1, tournament.id)
    reg = Registration(category_id=category.id, player_id=profile.id)
    db.session.add(reg)
    db.session.commit()

    response = client.post(url_for('player.cancel_registration', registration_id=reg.id), follow_redirects=True)
    assert response.status_code == 200
    # Check redirected to login - need request context for url_for in assertion
    # A simpler check might be for login page content
    assert b"Sign In" in response.data

def test_cancel_registration_fail_not_owner(client, init_database):
    """Test cancelling registration fails if logged-in user doesn't own it."""
    # Setup registration owned by user1
    user1 = User(username='owner', email='owner@test.com')
    db.session.add(user1)
    db.session.commit()
    profile1 = create_test_profile(user1.id)
    tournament = create_test_tournament(1, "Cancel Tourney")
    category = create_test_category(1, tournament.id)
    reg = Registration(category_id=category.id, player_id=profile1.id)
    db.session.add(reg)
    db.session.commit()
    reg_id = reg.id

    # Login as user2
    register_test_user(client, 'otheruser', 'other@test.com', 'password123')
    login_test_user(client, 'other@test.com', 'password123')

    # Attempt cancellation
    response = client.post(url_for('player.cancel_registration', registration_id=reg_id), follow_redirects=True)
    assert response.status_code == 200
    assert b"My Tournament Registrations" in response.data # Redirected back
    assert b"You do not have permission to cancel this registration." in response.data # Check flash

    # Verify registration still exists
    assert Registration.query.get(reg_id) is not None

def test_cancel_registration_fail_tournament_not_upcoming(client, init_database):
    """Test cancelling registration fails if tournament is ongoing or completed."""
    register_test_user(client, 'canceluser', 'cancel@test.com', 'password123')
    login_test_user(client, 'cancel@test.com', 'password123')
    user = User.query.filter_by(email='cancel@test.com').first()
    profile = create_test_profile(user.id)
    tournament = create_test_tournament(1, "Cancel Tourney", status=TournamentStatus.ONGOING) # Ongoing
    category = create_test_category(1, tournament.id)
    reg = Registration(category_id=category.id, player_id=profile.id)
    db.session.add(reg)
    db.session.commit()
    reg_id = reg.id

    response = client.post(url_for('player.cancel_registration', registration_id=reg_id), follow_redirects=True)
    assert response.status_code == 200
    assert b"Cannot cancel registration for tournaments that are ongoing or completed." in response.data
    assert Registration.query.get(reg_id) is not None # Verify not deleted

def test_cancel_registration_fail_paid(client, init_database):
    """Test cancelling registration fails if already paid/verified."""
    register_test_user(client, 'canceluser', 'cancel@test.com', 'password123')
    login_test_user(client, 'cancel@test.com', 'password123')
    user = User.query.filter_by(email='cancel@test.com').first()
    profile = create_test_profile(user.id)
    tournament = create_test_tournament(1, "Cancel Tourney", status=TournamentStatus.UPCOMING)
    category = create_test_category(1, tournament.id)
    reg = Registration(
        category_id=category.id,
        player_id=profile.id,
        payment_status='paid', # Paid
        payment_verified=True
    )
    db.session.add(reg)
    db.session.commit()
    reg_id = reg.id

    response = client.post(url_for('player.cancel_registration', registration_id=reg_id), follow_redirects=True)
    assert response.status_code == 200
    assert b"Registration has been paid. Please contact the organizer" in response.data
    assert Registration.query.get(reg_id) is not None # Verify not deleted


# TODO: Add tests for anonymous registration (account creation)