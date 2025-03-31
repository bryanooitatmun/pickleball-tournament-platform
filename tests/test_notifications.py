import pytest
from app import create_app, db, scheduler
from app.models import (
    User, UserRole, Tournament, TournamentCategory, Match,
    PlayerProfile, Registration, CategoryType
)
from app.tasks.email_tasks import send_match_reminder_email, send_schedule_change_email
from datetime import date, datetime, timedelta
from unittest.mock import patch, MagicMock
import os

basedir = os.path.abspath(os.path.dirname(__file__))



class TestConfig:
    """Test configuration for notification tests"""
    TESTING = True
    SECRET_KEY = 'test-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False
    MAIL_SERVER = 'localhost'
    MAIL_PORT = 25
    MAIL_USERNAME = None
    MAIL_PASSWORD = None
    MAIL_DEFAULT_SENDER = 'test@example.com'
    SOCKETIO_CORS_ALLOWED_ORIGINS = '*'
    SOCKETIO_ASYNC_MODE = 'eventlet'
    UPLOAD_FOLDER = os.path.join(basedir, 'app', 'static', 'tests', 'uploads')

# Helper functions
def create_test_user(db_session, username, role=UserRole.PLAYER, email=None):
    """Create a test user with the specified role"""
    if email is None:
        email = f"{username}@example.com"
        
    user = User(username=username, email=email, role=role)
    user.set_password("password")
    db_session.add(user)
    db_session.commit()
    
    # Create player profile if it's a player
    if role == UserRole.PLAYER:
        profile = PlayerProfile(
            user=user,
            full_name=f"{username.capitalize()} Testuser"
        )
        db_session.add(profile)
        db_session.commit()
    
    return user

def create_test_tournament(db_session, name="Test Tournament", organizer=None):
    """Create a test tournament"""
    tournament = Tournament(
        name=name,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=2),
        registration_deadline=date.today() - timedelta(days=1),
        organizer_id=organizer.id if organizer else None
    )
    db_session.add(tournament)
    db_session.commit()
    return tournament

def create_test_category(db_session, tournament, name="Men's Singles"):
    """Create a test category"""
    category = TournamentCategory(
        tournament_id=tournament.id,
        name=name,
        max_participants=16,
        category_type=CategoryType.MENS_SINGLES,
    )
    db_session.add(category)
    db_session.commit()
    return category

def create_test_match(db_session, category, player1, player2, round_num=1, 
                     court="Court 1", scheduled_time=None):
    """Create a test match between two players"""
    if scheduled_time is None:
        scheduled_time = datetime.now() + timedelta(days=1)
        
    match = Match(
        category_id=category.id,
        player1_id=player1.player_profile.id if hasattr(player1.player_profile, 'id') else player1.id,
        player2_id=player2.player_profile.id if hasattr(player2.player_profile, 'id') else player2.id,
        round=round_num,
        match_order=1,
        court=court,
        scheduled_time=scheduled_time
    )

    db_session.add(match)
    db_session.commit()
    return match

def create_test_registration(db_session, category, player):
    """Create a test registration"""
    reg = Registration(
        category_id=category.id,
        player_id=player.id if hasattr(player, 'id') else player.user_id,
        payment_status='paid'
    )
    db_session.add(reg)
    db_session.commit()
    return reg

# === Notification Tests ===

@pytest.fixture(scope='module')
def app():
    """Create Flask app for testing"""
    app = create_app(TestConfig)
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture(scope='function')
def notification_test_data(app):
    """Create test data for notification tests"""
    with app.app_context():
        # Clear database
        db.session.remove()
        db.drop_all()
        db.create_all()
        
        # Create users
        organizer = create_test_user(db.session, "notify_organizer", UserRole.ORGANIZER, 
                                   email="organizer@example.com")
        player1 = create_test_user(db.session, "notify_player1", UserRole.PLAYER, 
                                  email="player1@example.com")
        player2 = create_test_user(db.session, "notify_player2", UserRole.PLAYER, 
                                  email="player2@example.com")
        
        # Create tournament, category, and match
        tournament = create_test_tournament(db.session, "Notification Tournament", organizer)
        category = create_test_category(db.session, tournament)
        
        # Schedule match for tomorrow
        tomorrow = datetime.now() + timedelta(days=1)
        match = create_test_match(db.session, category, player1, player2, 
                                 scheduled_time=tomorrow)
        
        # Create registrations
        reg1 = create_test_registration(db.session, category, player1)
        reg2 = create_test_registration(db.session, category, player2)
        
        yield {
            'tournament': tournament,
            'category': category,
            'match': match,
            'organizer': organizer,
            'player1': player1,
            'player2': player2,
            'registration1': reg1,
            'registration2': reg2
        }
        
        # Clean up
        db.session.remove()

@patch('app.tasks.email_tasks.mail')
def test_match_reminder_email(mock_mail, notification_test_data, app):
    """Test match reminder email task"""
    with app.app_context():
        match = notification_test_data['match']
        player1 = notification_test_data['player1']
        player2 = notification_test_data['player2']
        
        # Call the reminder task
        send_match_reminder_email(match.id)
        
        # Verify emails were sent
        assert mock_mail.send.call_count == 2  # One email for each player
        
        # Get the Message objects passed to mail.send
        sent_messages = [call.args[0] for call in mock_mail.send.call_args_list]
        
        # Check recipient emails
        recipient_emails = [msg.recipients[0] for msg in sent_messages]
        assert player1.email in recipient_emails
        assert player2.email in recipient_emails
        
        # Check email content
        for msg in sent_messages:
            # Verify tournament name appears in subject
            assert notification_test_data['tournament'].name in msg.subject

            # Verify match details in body
            assert str(match.court) in msg.html
            assert match.scheduled_time.strftime("%d %B %Y") in msg.html
            

@patch('app.tasks.email_tasks.mail')
def test_schedule_change_email(mock_mail, notification_test_data, app):
    """Test match schedule change email task"""
    with app.app_context():
        match = notification_test_data['match']
        player1 = notification_test_data['player1']
        player2 = notification_test_data['player2']
        
        # Store original details
        original_court = match.court
        original_time = match.scheduled_time
        
        # Update match details
        new_time = original_time + timedelta(hours=2)
        new_court = "Court 5"
        
        # Call the notification task with the changes
        send_schedule_change_email(
            match.id, 
            {'court': new_court, 'scheduled_time': new_time}
        )
        
        # Verify emails were sent
        assert mock_mail.send.call_count == 2  # One email for each player
        
        # Get the Message objects passed to mail.send
        sent_messages = [call.args[0] for call in mock_mail.send.call_args_list]
        
        # Check recipient emails
        recipient_emails = [msg.recipients[0] for msg in sent_messages]
        assert player1.email in recipient_emails
        assert player2.email in recipient_emails
        
        # Check email content includes both old and new details
        for msg in sent_messages:
            # Verify change notification in subject
            assert "Schedule Change" in msg.subject
            
            # Verify new details in body
            assert str(new_court) in msg.html  # New court
            assert new_time.strftime("%I:%M") in msg.html  # New time

@patch('app.tasks.email_tasks.mail')
def test_automatic_reminder_scheduling(mock_mail, notification_test_data, app):
    """Test automatic scheduling of match reminders"""
    with app.app_context():
        match = notification_test_data['match']
        
        # Create a simple mock scheduler
        mock_scheduler = MagicMock()
        
        # Get the real current_app from Flask and attach our mock scheduler
        from flask import current_app
        
        # Store original scheduler if it exists
        has_original_scheduler = hasattr(current_app, 'scheduler')
        original_scheduler = getattr(current_app, 'scheduler', None)
        
        # Attach our mock
        current_app.scheduler = mock_scheduler
        
        try:
            # Set match time to be 24 hours and 5 minutes in the future
            future_time = datetime.now() + timedelta(hours=24, minutes=5)
            match.scheduled_time = future_time
            db.session.commit()
            
            # Call the function that would normally schedule reminders
            from app.tasks.match_tasks import schedule_match_reminders
            schedule_match_reminders(match.id)
            
            # Verify that add_job was called at least once
            assert mock_scheduler.add_job.call_count >= 1
        finally:
            # Restore original scheduler or remove our mock
            if has_original_scheduler:
                current_app.scheduler = original_scheduler
            else:
                delattr(current_app, 'scheduler')

@patch('app.tasks.email_tasks.mail')
def test_schedule_change_triggers_notification(mock_mail, notification_test_data, app):
    """Test that changing a match schedule triggers notification"""
    with app.app_context():
        match_id = notification_test_data['match'].id
        
        # Get original values by fetching fresh from the database
        match = Match.query.get(match_id)
        original_court = match.court
        original_time = match.scheduled_time
        
        # Create clearly different values
        new_court = "COMPLETELY_NEW_COURT"
        new_time = original_time + timedelta(hours=5)
        
        # Mock the send_schedule_change_email function to verify it's called
        with patch('app.tasks.match_tasks.send_schedule_change_email') as mock_send:
            # Update match details and force commit
            match.court = new_court
            match.scheduled_time = new_time
            db.session.commit()
            db.session.flush()
            
            # Verify changes were actually applied by re-fetching
            updated_match = Match.query.get(match_id)
            print(f"Verification - Original court: {original_court}, New court: {updated_match.court}")
            print(f"Verification - Original time: {original_time}, New time: {updated_match.scheduled_time}")
            
            # Now call the function to check changes with the original values
            from app.tasks.match_tasks import check_schedule_changes
            check_schedule_changes(match_id, original_court, original_time)
            
            # Verify notification task was called
            mock_send.assert_called_once_with(
                match_id,
                {'court': new_court, 'scheduled_time': new_time}
            )