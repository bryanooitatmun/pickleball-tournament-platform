import pytest
import json
from flask_socketio import SocketIOTestClient, SocketIO
from app import create_app, db, socketio
from app.models import (
    User, UserRole, Tournament, TournamentCategory, Match, 
    MatchScore, CategoryType, PlayerProfile, Registration
)
from datetime import date, timedelta, datetime
import os

basedir = os.path.abspath(os.path.dirname(__file__))

class TestConfig:
    """Test configuration for SocketIO tests"""
    TESTING = True
    SECRET_KEY = 'test-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False
    SERVER_NAME = 'localhost.localdomain'
    PRESERVE_CONTEXT_ON_EXCEPTION = False
    SOCKETIO_CORS_ALLOWED_ORIGINS = '*'
    SOCKETIO_ASYNC_MODE = 'eventlet'
    UPLOAD_FOLDER = os.path.join(basedir, 'app', 'static', 'tests', 'uploads')

# Helper functions
def create_test_user(db_session, username, role=UserRole.PLAYER):
    """Create a test user with the specified role"""
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

def create_test_category(db_session, tournament, name="Men's Singles", category_type=CategoryType.MENS_SINGLES):
    """Create a test category"""
    category = TournamentCategory(
        tournament_id=tournament.id,
        name=name,
        category_type=category_type,
        max_participants=16
    )
    db_session.add(category)
    db_session.commit()
    return category

def create_test_match(db_session, category, player1, player2, round_num=1, court="Court 1"):
    """Create a test match between two players"""
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

# === SocketIO Tests ===

@pytest.fixture(scope='module')
def socketio_app():
    """Create Flask app with SocketIO for testing"""
    app = create_app(TestConfig)
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture(scope='function')
def socketio_client(socketio_app):
    """Create a SocketIO test client"""
    return SocketIOTestClient(socketio_app, socketio)

@pytest.fixture(scope='function')
def socket_test_data(socketio_app):
    """Create test data for SocketIO tests"""
    with socketio_app.app_context():
        # Clear database
        db.session.remove()
        db.drop_all()
        db.create_all()
        
        # Create users
        organizer = create_test_user(db.session, "socket_organizer", UserRole.ORGANIZER)
        referee = create_test_user(db.session, "socket_referee", UserRole.REFEREE)
        player1 = create_test_user(db.session, "socket_player1", UserRole.PLAYER)
        player2 = create_test_user(db.session, "socket_player2", UserRole.PLAYER)
        
        # Create tournament, category, and match
        tournament = create_test_tournament(db.session, "SocketIO Tournament", organizer)
        category = create_test_category(db.session, tournament)
        match = create_test_match(db.session, category, player1, player2)
        
        yield {
            'tournament': tournament,
            'category': category,
            'match': match,
            'organizer': organizer,
            'referee': referee,
            'player1': player1,
            'player2': player2
        }
        
        # Clean up
        db.session.remove()

def test_connect_to_tournament_room(socketio_client, socket_test_data, socketio_app):
    """Connect to tournament room"""
    with socketio_app.test_client() as client:
        # Log in as user
        response = client.post(
            '/auth/login',
            data=dict(email="socket_player1@example.com", password="password"),
            follow_redirects=True
        )

        # Join tournament room
        tournament_id = socket_test_data['tournament'].id
        match_id = socket_test_data['match'].id
        socketio_client.emit('join', {'room': f'tournament_{tournament_id}'})

    assert len(received) > 0

def test_score_update_event(socketio_client, socket_test_data, socketio_app):
    """Test that score updates are broadcast to tournament room"""
    with socketio_app.test_client() as client:
        # Log in as referee
        client.post(
            '/auth/login',
            data=dict(email="socket_referee@example.com", password="password"),
            follow_redirects=True
        )
        
        # Join tournament room
        tournament_id = socket_test_data['tournament'].id
        match_id = socket_test_data['match'].id
        socketio_client.emit('join', {'room': f'tournament_{tournament_id}'})
        
        # Enter scores via HTTP request using the correct organizer route
        response = client.post(
            f'/organizer/tournament/{tournament_id}/update_match/{match_id}',
            data={
                'court': socket_test_data['match'].court,
                'scheduled_time': (date.today() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M"),
                'livestream_url': "https://youtube.com/watch?v=12345",
                'set_count': 2,
                'scores-0-player1_score': 11,
                'scores-0-player2_score': 9,
                'scores-1-player1_score': 11,
                'scores-1-player2_score': 7
            },
            follow_redirects=True
        )
        
        # Check received score update event
        received = socketio_client.get_received()

        # Find score update events
        score_events = [event for event in received if event['name'] == 'match_update']
        assert len(score_events) > 0
        
        # Check event data
        event_data = score_events[0]['args'][0]['match']
        assert event_data['id'] == match_id
        assert 'scores' in event_data or 'player1_score' in event_data
        
        # The assertions below might need to be adjusted based on the actual score update event format
        if 'scores' in event_data:
            # Check score details if full scores are provided
            scores = event_data['scores']
            assert len(scores) == 2  # Two sets
            
            # Check score details
            set1 = scores[0]
            assert set1 is not None
            assert set1['player1_score'] == 11
            assert set1['player2_score'] == 9
            
            set2 = scores[1]
            assert set2 is not None
            assert set2['player1_score'] == 11
            assert set2['player2_score'] == 7
        elif 'player1_score' in event_data:
            # If only the latest set score is provided
            assert event_data['player1_score'] == 11
            assert event_data['player2_score'] == 7
            assert event_data['set_number'] == 2

# def test_match_verification_event(socketio_client, socket_test_data, socketio_app):
#     """Test that match verification events are broadcast"""
#     with socketio_app.test_client() as client:
#         # Log in as referee first
#         client.post(
#             '/auth/login',
#             data=dict(email="socket_referee@example.com", password="password"),
#             follow_redirects=True
#         )
        
#         # Join tournament room
#         tournament_id = socket_test_data['tournament'].id
#         match_id = socket_test_data['match'].id
#         socketio_client.emit('join', {'room': f'tournament_{tournament_id}'})
        
#         # Enter scores and verify as referee
#         client.post(
#             f'/organizer/tournament/{tournament_id}/update_match/{match_id}',
#             data={
#                 'court': socket_test_data['match'].court,
#                 'scheduled_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#                 'livestream_url': "https://youtube.com/watch?v=12345",
#                 'set_count': 2,
#                 'scores-0-player1_score': 11,
#                 'scores-0-player2_score': 9,
#                 'scores-1-player1_score': 11,
#                 'scores-1-player2_score': 7
#             },
#             follow_redirects=True
#         )
        
#         # Get and clear received events
#         socketio_client.get_received()
        
#         # Now log in as player and verify
#         client.get('/auth/logout', follow_redirects=True)
#         client.post(
#             '/auth/login',
#             data=dict(email="socket_player1@example.com", password="password"),
#             follow_redirects=True
#         )
        
#         # Verify match as player
#         client.post(
#             f'/player/match/{match_id}/verify',
#             follow_redirects=True
#         )
        
#         # Check received verification event
#         received = socketio_client.get_received()
        
#         # Find verification events - either 'match_verified' or 'match_updated'
#         verification_events = [event for event in received if event['name'] in ['match_verified', 'match_updated']]
#         assert len(verification_events) > 0
        
#         # Check event data
#         event_data = verification_events[0]['args'][0]
#         if 'match_id' in event_data:
#             assert event_data['match_id'] == match_id
#         elif 'match' in event_data and 'id' in event_data['match']:
#             assert event_data['match']['id'] == match_id
        
#         # Check status if available
#         if 'status' in event_data:
#             assert event_data['status'] == 'completed'

# def test_court_assignment_event(socketio_client, socket_test_data, socketio_app):
#     """Test that court assignment changes are broadcast"""
#     with socketio_app.test_client() as client:
#         # Log in as organizer
#         client.post(
#             '/auth/login',
#             data=dict(email="socket_organizer@example.com", password="password"),
#             follow_redirects=True
#         )
        
#         # Join tournament room
#         tournament_id = socket_test_data['tournament'].id
#         match_id = socket_test_data['match'].id
#         socketio_client.emit('join', {'room': f'tournament_{tournament_id}'})
        
#         # Update match court assignment
#         client.post(
#             f'/organizer/tournament/{tournament_id}/update_match/{match_id}',
#             data={
#                 'court': "Court 2",  # Change court from Court 1 to Court 2
#                 'scheduled_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#                 'livestream_url': "https://youtube.com/watch?v=12345",
#                 'set_count': 0  # No scores, just updating court
#                 # Not including any score fields since set_count=0
#             },
#             follow_redirects=True
#         )
        
#         # Check received court assignment event
#         received = socketio_client.get_received()
        
#         # Find court assignment events
#         court_events = [event for event in received if event['name'] in ['court_update', 'match_update']]
#         assert len(court_events) > 0
        
#         # Check event data - format may vary based on the actual implementation
#         event_data = court_events[0]['args'][0]
        
#         # The event might include the court directly or as part of a match object
#         if 'court' in event_data:
#             assert event_data['court'] == "Court 2"
#         elif 'match' in event_data and 'court' in event_data['match']:
#             assert event_data['match']['court'] == "Court 2"

# def test_check_in_event(socketio_client, socket_test_data, socketio_app):
#     """Test that player check-in events are broadcast"""
#     with socketio_app.test_client() as client:
#         # Create registration for player
#         with socketio_app.app_context():
#             registration = Registration(
#                 category_id=socket_test_data['category'].id,
#                 player_id=socket_test_data['player1'].id if hasattr(socket_test_data['player1'], 'id') else socket_test_data['player1'].user_id,
#                 payment_status='verified',
#                 checked_in=False
#             )
#             db.session.add(registration)
#             db.session.commit()
#             reg_id = registration.id
        
#         # Log in as player
#         client.post(
#             '/auth/login',
#             data=dict(email="socket_player1@example.com", password="password"),
#             follow_redirects=True
#         )
        
#         # Join tournament room
#         tournament_id = socket_test_data['tournament'].id
#         socketio_client.emit('join', {'room': f'tournament_{tournament_id}'})
        
#         # Player checks in
#         client.post(
#             f'/player/registration/{reg_id}/check_in',
#             follow_redirects=True
#         )
        
#         # Check received check-in event
#         received = socketio_client.get_received()
        
#         # Find check-in events
#         checkin_events = [event for event in received if event['name'] == 'player_checkin']
#         assert len(checkin_events) > 0
        
#         # Check event data
#         event_data = checkin_events[0]['args'][0]
#         assert event_data['registration_id'] == reg_id
#         assert event_data['player_id'] == (socket_test_data['player1'].id if hasattr(socket_test_data['player1'], 'id') else socket_test_data['player1'].user_id)
#         assert event_data['checked_in'] is True

# def test_bracket_update_event(socketio_client, socket_test_data, socketio_app):
#     """Test that bracket updates are broadcast when match results are finalized"""
#     with socketio_app.test_client() as client:
#         # Setup: First create necessary match structure
#         with socketio_app.app_context():
#             tournament = socket_test_data['tournament']
#             category = socket_test_data['category']
#             player1 = socket_test_data['player1']
#             player2 = socket_test_data['player2']
            
#             # Create a next round match that will be updated
#             next_match = Match(
#                 category_id=category.id,
#                 round=1,  # Final
#                 match_order=1
#             )
#             db.session.add(next_match)
#             db.session.commit()
            
#             # Link current match to next match
#             match = socket_test_data['match']
#             match.next_match_id = next_match.id
#             match.round = 2  # Semi-final
#             db.session.commit()
            
#             # Add scores to make player1 the winner
#             score1 = MatchScore(match_id=match.id, set_number=1, player1_score=11, player2_score=9)
#             score2 = MatchScore(match_id=match.id, set_number=2, player1_score=11, player2_score=7)
#             db.session.add_all([score1, score2])
            
#             # Mark match as referee verified
#             match.referee_verified = True
#             match.winning_player_id = player1.id if hasattr(player1, 'id') else player1.user_id
#             match.losing_player_id = player2.id if hasattr(player2, 'id') else player2.user_id
#             db.session.commit()
            
#             next_match_id = next_match.id
        
#         # Log in as player
#         client.post(
#             '/auth/login',
#             data=dict(email="socket_player1@example.com", password="password"),
#             follow_redirects=True
#         )
        
#         # Join tournament room
#         tournament_id = socket_test_data['tournament'].id
#         match_id = socket_test_data['match'].id
#         socketio_client.emit('join', {'room': f'tournament_{tournament_id}'})
        
#         # Complete match verification (which should trigger bracket update)
#         client.post(
#             f'/player/match/{match_id}/verify',
#             follow_redirects=True
#         )
        
#         # Check received bracket update event
#         received = socketio_client.get_received()
        
#         # Find bracket update events (could be 'bracket_update' or related name)
#         bracket_events = [event for event in received if 'bracket' in event['name'] or 'match' in event['name']]
#         assert len(bracket_events) > 0
        
#         # Check that next match was updated with winner as player1
#         with socketio_app.app_context():
#             updated_next_match = Match.query.get(next_match_id)
#             assert updated_next_match.player1_id == (player1.id if hasattr(player1, 'id') else player1.user_id)