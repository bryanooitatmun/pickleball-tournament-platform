import pytest
from flask import url_for, session
from app import db
from app.models import User, PlayerProfile, UserRole, Tournament, TournamentStatus, TournamentCategory, Registration, Feedback
from datetime import date, timedelta, datetime

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

def create_test_tournament(id, name="Test Tournament", status=TournamentStatus.UPCOMING):
    tournament = Tournament(id=id, name=name, status=status, start_date=date.today(), end_date=date.today() + timedelta(days=1))
    db.session.add(tournament)
    db.session.commit()
    return tournament

def create_test_category(id, tournament_id, name="Test Category"):
    category = TournamentCategory(id=id, tournament_id=tournament_id, name=name)
    db.session.add(category)
    db.session.commit()
    return category

def create_test_registration(id, category_id, player_id):
    reg = Registration(id=id, category_id=category_id, player_id=player_id)
    db.session.add(reg)
    db.session.commit()
    return reg

# --- Test Cases for submit_tournament_feedback ---

def test_submit_feedback_access_denied_not_logged_in(client, init_database):
    """Test accessing submit_tournament_feedback without login."""
    t = create_test_tournament(1)
    response = client.get(url_for('player.submit_tournament_feedback', tournament_id=t.id), follow_redirects=False)
    assert response.status_code == 302
    assert url_for('auth.login') in response.location

def test_submit_feedback_fail_no_profile(client, init_database):
    """Test accessing submit_tournament_feedback with no profile."""
    register_test_user(client, 'feedback_np', 'fb_np@test.com', 'password123')
    login_test_user(client, 'fb_np@test.com', 'password123')
    t = create_test_tournament(1)

    response = client.get(url_for('player.submit_tournament_feedback', tournament_id=t.id), follow_redirects=False)
    assert response.status_code == 302 # Redirects via @player_required
    assert url_for('player.create_profile') in response.location

def test_submit_feedback_fail_tournament_not_completed(client, init_database):
    """Test submitting feedback fails if tournament is not completed."""
    register_test_user(client, 'feedback_user', 'fb@test.com', 'password123')
    login_test_user(client, 'fb@test.com', 'password123')
    user = User.query.filter_by(email='fb@test.com').first()
    create_test_profile(user.id)
    # Tournament is ONGOING, not COMPLETED
    t = create_test_tournament(1, name="Ongoing Tourney", status=TournamentStatus.ONGOING)

    response = client.get(url_for('player.submit_tournament_feedback', tournament_id=t.id), follow_redirects=True)
    assert response.status_code == 200
    assert b'Feedback can only be submitted after tournament completion.' in response.data
    # Should redirect to tournament detail page
    assert f'{t.name}'.encode('utf-8') in response.data # Check tournament name on detail page

def test_submit_feedback_fail_not_participant(client, init_database):
    """Test submitting feedback fails if user did not participate."""
    register_test_user(client, 'feedback_user', 'fb@test.com', 'password123')
    login_test_user(client, 'fb@test.com', 'password123')
    user = User.query.filter_by(email='fb@test.com').first()
    create_test_profile(user.id)
    # Tournament is COMPLETED, but user has no registration
    t = create_test_tournament(1, name="Completed Tourney", status=TournamentStatus.COMPLETED)
    c = create_test_category(1, t.id)
    # Create registration for another user
    other_user = User(username='other', email='o@test.com'); db.session.add(other_user); db.session.commit()
    other_profile = create_test_profile(other_user.id)
    create_test_registration(1, c.id, other_profile.id)

    response = client.get(url_for('player.submit_tournament_feedback', tournament_id=t.id), follow_redirects=True)
    assert response.status_code == 200
    assert b'Only participants can submit feedback.' in response.data
    assert f'{t.name}'.encode('utf-8') in response.data # Check tournament name on detail page

def test_submit_feedback_redirect_if_already_submitted(client, init_database):
    """Test redirect to edit page if feedback already exists for the tournament."""
    register_test_user(client, 'feedback_user', 'fb@test.com', 'password123')
    login_test_user(client, 'fb@test.com', 'password123')
    user = User.query.filter_by(email='fb@test.com').first()
    profile = create_test_profile(user.id)
    t = create_test_tournament(1, status=TournamentStatus.COMPLETED)
    c = create_test_category(1, t.id)
    create_test_registration(1, c.id, profile.id) # User participated

    # Create existing feedback
    existing_fb = Feedback(user_id=user.id, tournament_id=t.id, rating=4, comment="Old feedback")
    db.session.add(existing_fb)
    db.session.commit()

    response = client.get(url_for('player.submit_tournament_feedback', tournament_id=t.id), follow_redirects=False)
    assert response.status_code == 302
    assert url_for('player.edit_feedback', feedback_id=existing_fb.id) in response.location

    response_redirected = client.get(url_for('player.submit_tournament_feedback', tournament_id=t.id), follow_redirects=True)
    assert b'You have already submitted feedback for this tournament.' in response_redirected.data
    assert b'Edit Feedback' in response_redirected.data # Check edit page title

def test_submit_feedback_get_page(client, init_database):
    """Test GET request renders the feedback form correctly."""
    register_test_user(client, 'feedback_user', 'fb@test.com', 'password123')
    login_test_user(client, 'fb@test.com', 'password123')
    user = User.query.filter_by(email='fb@test.com').first()
    profile = create_test_profile(user.id)
    t = create_test_tournament(1, name="Feedback Tourney", status=TournamentStatus.COMPLETED)
    c = create_test_category(1, t.id)
    create_test_registration(1, c.id, profile.id) # User participated

    response = client.get(url_for('player.submit_tournament_feedback', tournament_id=t.id))
    assert response.status_code == 200
    assert b'Feedback for Feedback Tourney' in response.data
    assert b'Rating' in response.data
    assert b'Comment' in response.data
    assert b'Submit Anonymously' in response.data

def test_submit_feedback_post_success(client, init_database):
    """Test successful feedback submission via POST."""
    register_test_user(client, 'feedback_user', 'fb@test.com', 'password123')
    login_test_user(client, 'fb@test.com', 'password123')
    user = User.query.filter_by(email='fb@test.com').first()
    profile = create_test_profile(user.id)
    t = create_test_tournament(1, name="Feedback Tourney", status=TournamentStatus.COMPLETED)
    c = create_test_category(1, t.id)
    create_test_registration(1, c.id, profile.id) # User participated

    data = {
        'rating': 5,
        'comment': 'Great tournament!',
        'is_anonymous': False,
        'tournament_id': t.id # Hidden field
    }
    response = client.post(url_for('player.submit_tournament_feedback', tournament_id=t.id), data=data, follow_redirects=True)

    assert response.status_code == 200
    assert b'Your feedback has been submitted. Thank you!' in response.data
    # Should redirect to tournament detail page
    assert f'{t.name}'.encode('utf-8') in response.data

    # Verify feedback exists in DB
    feedback = Feedback.query.filter_by(user_id=user.id, tournament_id=t.id).first()
    assert feedback is not None
    assert feedback.rating == 5
    assert feedback.comment == 'Great tournament!'
    assert feedback.is_anonymous is False

# --- Test Cases for submit_organizer_feedback ---

def test_submit_organizer_feedback_access_denied_not_logged_in(client, init_database):
    """Test accessing submit_organizer_feedback without login."""
    # Need a dummy organizer user to generate URL
    org = User(username='org', email='org@test.com', role=UserRole.ORGANIZER); db.session.add(org); db.session.commit()
    response = client.get(url_for('player.submit_organizer_feedback', organizer_id=org.id), follow_redirects=False)
    assert response.status_code == 302
    assert url_for('auth.login') in response.location

def test_submit_organizer_feedback_fail_no_profile(client, init_database):
    """Test accessing submit_organizer_feedback with no profile."""
    register_test_user(client, 'feedback_org_np', 'fb_org_np@test.com', 'password123')
    login_test_user(client, 'fb_org_np@test.com', 'password123')
    org = User(username='org', email='org@test.com', role=UserRole.ORGANIZER); db.session.add(org); db.session.commit()

    response = client.get(url_for('player.submit_organizer_feedback', organizer_id=org.id), follow_redirects=False)
    assert response.status_code == 302 # Redirects via @player_required
    assert url_for('player.create_profile') in response.location

def test_submit_organizer_feedback_fail_organizer_not_found(client, init_database):
    """Test submitting feedback for a non-existent organizer ID."""
    register_test_user(client, 'feedback_user', 'fb@test.com', 'password123')
    login_test_user(client, 'fb@test.com', 'password123')
    user = User.query.filter_by(email='fb@test.com').first()
    create_test_profile(user.id)

    response = client.get(url_for('player.submit_organizer_feedback', organizer_id=999))
    assert response.status_code == 404

def test_submit_organizer_feedback_redirect_if_already_submitted(client, init_database):
    """Test redirect to edit page if feedback already exists for the organizer."""
    register_test_user(client, 'feedback_user', 'fb@test.com', 'password123')
    login_test_user(client, 'fb@test.com', 'password123')
    user = User.query.filter_by(email='fb@test.com').first()
    create_test_profile(user.id)
    org = User(username='org', email='org@test.com', role=UserRole.ORGANIZER); db.session.add(org); db.session.commit()

    # Create existing feedback
    existing_fb = Feedback(user_id=user.id, organizer_id=org.id, rating=3, comment="Old org feedback")
    db.session.add(existing_fb)
    db.session.commit()

    response = client.get(url_for('player.submit_organizer_feedback', organizer_id=org.id), follow_redirects=False)
    assert response.status_code == 302
    assert url_for('player.edit_feedback', feedback_id=existing_fb.id) in response.location

    response_redirected = client.get(url_for('player.submit_organizer_feedback', organizer_id=org.id), follow_redirects=True)
    assert b'You have already submitted feedback for this organizer.' in response_redirected.data
    assert b'Edit Feedback' in response_redirected.data

def test_submit_organizer_feedback_get_page(client, init_database):
    """Test GET request renders the feedback form correctly for an organizer."""
    register_test_user(client, 'feedback_user', 'fb@test.com', 'password123')
    login_test_user(client, 'fb@test.com', 'password123')
    user = User.query.filter_by(email='fb@test.com').first()
    create_test_profile(user.id)
    org = User(username='org_user', email='org@test.com', role=UserRole.ORGANIZER); db.session.add(org); db.session.commit()

    response = client.get(url_for('player.submit_organizer_feedback', organizer_id=org.id))
    assert response.status_code == 200
    assert b'Feedback for org_user' in response.data
    assert b'Rating' in response.data
    assert b'Comment' in response.data

def test_submit_organizer_feedback_post_success(client, init_database):
    """Test successful organizer feedback submission via POST."""
    register_test_user(client, 'feedback_user', 'fb@test.com', 'password123')
    login_test_user(client, 'fb@test.com', 'password123')
    user = User.query.filter_by(email='fb@test.com').first()
    create_test_profile(user.id)
    org = User(username='org_user', email='org@test.com', role=UserRole.ORGANIZER); db.session.add(org); db.session.commit()

    data = {
        'rating': 4,
        'comment': 'Well organized!',
        'is_anonymous': True,
        'organizer_id': org.id # Hidden field
    }
    # Assuming redirect goes to main.organizer_detail which might not exist or require setup
    # For now, just check the flash and DB, ignore redirect target content
    # Need to mock or create the organizer_detail route for a 200 response
    with patch('app.main.routes.render_template') as mock_render: # Mock rendering to avoid needing template/route
        mock_render.return_value = "Organizer Detail Page"
        response = client.post(url_for('player.submit_organizer_feedback', organizer_id=org.id), data=data, follow_redirects=True)

    assert response.status_code == 200 # Should now be 200 due to mocked redirect target
    assert b'Your feedback has been submitted. Thank you!' in response.data

    # Verify feedback exists in DB
    feedback = Feedback.query.filter_by(user_id=user.id, organizer_id=org.id).first()
    assert feedback is not None
    assert feedback.rating == 4
    assert feedback.comment == 'Well organized!'
    assert feedback.is_anonymous is True
    assert feedback.tournament_id is None # Ensure tournament_id is not set

# --- Test Cases for edit_feedback ---

def test_edit_feedback_access_denied_not_logged_in(client, init_database):
    """Test accessing edit_feedback without login."""
    # Need dummy feedback to generate URL
    user = User(username='dummy', email='d@test.com'); db.session.add(user); db.session.commit()
    fb = Feedback(user_id=user.id, rating=1); db.session.add(fb); db.session.commit()
    response = client.get(url_for('player.edit_feedback', feedback_id=fb.id), follow_redirects=False)
    assert response.status_code == 302
    assert url_for('auth.login') in response.location

def test_edit_feedback_fail_no_profile(client, init_database):
    """Test accessing edit_feedback with no profile."""
    register_test_user(client, 'editfb_np', 'efb_np@test.com', 'password123')
    login_test_user(client, 'efb_np@test.com', 'password123')
    user = User.query.filter_by(email='efb_np@test.com').first()
    # Need dummy feedback associated with user ID
    fb = Feedback(user_id=user.id, rating=1); db.session.add(fb); db.session.commit()

    response = client.get(url_for('player.edit_feedback', feedback_id=fb.id), follow_redirects=False)
    assert response.status_code == 302 # Redirects via @player_required
    assert url_for('player.create_profile') in response.location

def test_edit_feedback_fail_not_owner(client, init_database):
    """Test editing feedback fails if user doesn't own it."""
    # Feedback owner
    user1 = User(username='owner_fb', email='owner_fb@test.com'); db.session.add(user1); db.session.commit()
    fb = Feedback(user_id=user1.id, rating=1); db.session.add(fb); db.session.commit()

    # Logged-in user (different user)
    register_test_user(client, 'editor_fb', 'editor_fb@test.com', 'password123')
    login_test_user(client, 'editor_fb@test.com', 'password123')
    user2 = User.query.filter_by(email='editor_fb@test.com').first()
    create_test_profile(user2.id) # Need profile to pass @player_required

    response = client.get(url_for('player.edit_feedback', feedback_id=fb.id))
    assert response.status_code == 403 # Forbidden

    response = client.post(url_for('player.edit_feedback', feedback_id=fb.id), data={'rating': 5})
    assert response.status_code == 403 # Forbidden

def test_edit_feedback_get_page(client, init_database):
    """Test GET request renders edit form with pre-filled data."""
    register_test_user(client, 'editor_fb', 'editor_fb@test.com', 'password123')
    login_test_user(client, 'editor_fb@test.com', 'password123')
    user = User.query.filter_by(email='editor_fb@test.com').first()
    create_test_profile(user.id)
    t = create_test_tournament(1)
    fb = Feedback(user_id=user.id, tournament_id=t.id, rating=3, comment="Initial comment", is_anonymous=True)
    db.session.add(fb)
    db.session.commit()

    response = client.get(url_for('player.edit_feedback', feedback_id=fb.id))
    assert response.status_code == 200
    assert b'Edit Feedback' in response.data
    # Check pre-filled values (adjust based on form field types/names)
    assert b'value="3"' in response.data or b'value=3' in response.data # Rating
    assert b'Initial comment</textarea>' in response.data # Comment
    assert b'checked' in response.data # Anonymous checkbox

def test_edit_feedback_post_success_tournament(client, init_database):
    """Test successful update of tournament feedback via POST."""
    register_test_user(client, 'editor_fb', 'editor_fb@test.com', 'password123')
    login_test_user(client, 'editor_fb@test.com', 'password123')
    user = User.query.filter_by(email='editor_fb@test.com').first()
    create_test_profile(user.id)
    t = create_test_tournament(1, name="Edit Feedback Tourney")
    fb = Feedback(user_id=user.id, tournament_id=t.id, rating=3, comment="Initial")
    db.session.add(fb)
    db.session.commit()

    data = {
        'rating': 5,
        'comment': 'Updated comment!',
        'is_anonymous': True,
        'tournament_id': t.id # Hidden field might be needed by form
    }
    response = client.post(url_for('player.edit_feedback', feedback_id=fb.id), data=data, follow_redirects=True)

    assert response.status_code == 200
    assert b'Your feedback has been updated.' in response.data
    # Should redirect to tournament detail
    assert f'{t.name}'.encode('utf-8') in response.data

    # Verify DB update
    db.session.refresh(fb)
    assert fb.rating == 5
    assert fb.comment == 'Updated comment!'
    assert fb.is_anonymous is True
    assert fb.updated_at is not None

def test_edit_feedback_post_success_organizer(client, init_database):
    """Test successful update of organizer feedback via POST."""
    register_test_user(client, 'editor_fb', 'editor_fb@test.com', 'password123')
    login_test_user(client, 'editor_fb@test.com', 'password123')
    user = User.query.filter_by(email='editor_fb@test.com').first()
    create_test_profile(user.id)
    org = User(username='org_edit', email='org_e@test.com', role=UserRole.ORGANIZER); db.session.add(org); db.session.commit()
    fb = Feedback(user_id=user.id, organizer_id=org.id, rating=2, comment="Okay")
    db.session.add(fb)
    db.session.commit()

    data = {
        'rating': 1,
        'comment': 'Actually, not good.',
        'is_anonymous': False,
        'organizer_id': org.id # Hidden field
    }
    # Mock redirect target
    with patch('app.main.routes.render_template') as mock_render:
        mock_render.return_value = "Organizer Detail Page"
        response = client.post(url_for('player.edit_feedback', feedback_id=fb.id), data=data, follow_redirects=True)

    assert response.status_code == 200
    assert b'Your feedback has been updated.' in response.data

    # Verify DB update
    db.session.refresh(fb)
    assert fb.rating == 1
    assert fb.comment == 'Actually, not good.'
    assert fb.is_anonymous is False
    assert fb.updated_at is not None


# --- Test Cases for my_feedback ---

def test_my_feedback_access_denied_not_logged_in(client, init_database):
    """Test accessing my_feedback without login."""
    response = client.get(url_for('player.my_feedback'), follow_redirects=False)
    assert response.status_code == 302
    assert url_for('auth.login') in response.location

def test_my_feedback_fail_no_profile(client, init_database):
    """Test accessing my_feedback with no profile."""
    register_test_user(client, 'myfb_np', 'myfb_np@test.com', 'password123')
    login_test_user(client, 'myfb_np@test.com', 'password123')

    response = client.get(url_for('player.my_feedback'), follow_redirects=False)
    assert response.status_code == 302 # Redirects via @player_required
    assert url_for('player.create_profile') in response.location

def test_my_feedback_empty(client, init_database):
    """Test my_feedback page when user has no feedback submitted."""
    register_test_user(client, 'myfb_user', 'myfb@test.com', 'password123')
    login_test_user(client, 'myfb@test.com', 'password123')
    user = User.query.filter_by(email='myfb@test.com').first()
    create_test_profile(user.id)

    response = client.get(url_for('player.my_feedback'))
    assert response.status_code == 200
    assert b'My Feedback' in response.data
    # Check for message indicating no feedback (adjust based on template)
    assert b'You have not submitted any feedback yet.' in response.data

def test_my_feedback_displays_data(client, init_database):
    """Test my_feedback page displays submitted feedback correctly."""
    register_test_user(client, 'myfb_user', 'myfb@test.com', 'password123')
    login_test_user(client, 'myfb@test.com', 'password123')
    user = User.query.filter_by(email='myfb@test.com').first()
    create_test_profile(user.id)

    # Create feedback for a tournament
    t = create_test_tournament(1, name="My Feedback Tourney")
    fb1 = Feedback(user_id=user.id, tournament_id=t.id, rating=5, comment="Tourney feedback", created_at=datetime.utcnow() - timedelta(days=1))
    # Create feedback for an organizer
    org = User(username='myfb_org', email='myfb_o@test.com', role=UserRole.ORGANIZER); db.session.add(org); db.session.commit()
    fb2 = Feedback(user_id=user.id, organizer_id=org.id, rating=2, comment="Org feedback", is_anonymous=True, created_at=datetime.utcnow())
    db.session.add_all([fb1, fb2])
    db.session.commit()

    response = client.get(url_for('player.my_feedback'))
    assert response.status_code == 200
    assert b'My Feedback' in response.data

    # Check feedback details are present (order is desc by created_at)
    # Check fb2 (newer)
    assert b'Feedback for: Organizer myfb_org' in response.data # Check target display
    assert b'Rating: 2' in response.data
    assert b'Comment: Org feedback' in response.data
    assert b'(Anonymous)' in response.data
    # Check fb1 (older)
    assert b'Feedback for: Tournament My Feedback Tourney' in response.data
    assert b'Rating: 5' in response.data
    assert b'Comment: Tourney feedback' in response.data
    assert b'(Anonymous)' not in response.data # Should not be anonymous

    # Check edit links are present
    assert url_for('player.edit_feedback', feedback_id=fb1.id).encode('utf-8') in response.data
    assert url_for('player.edit_feedback', feedback_id=fb2.id).encode('utf-8') in response.data