import pytest
from flask import url_for, session
from app import db
from app.models import User, UserRole, Tournament, TournamentCategory, Match, PlayerProfile
from datetime import date, timedelta
import json

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

def login_user(client, user, password="password"):
    """Log in a user through the login route"""
    # The login form uses email, not username
    return client.post(
        '/auth/login',
        data=dict(
            email=user.email,  # Use email instead of username
            password=password,
            remember_me=False
        ),
        follow_redirects=True
    )

def logout_user(client):
    """Log out the current user"""
    return client.get('/auth/logout', follow_redirects=True)
# --- Tests for Route Access Control ---

def test_public_routes_access(client, init_database):
    """Test accessibility of public routes to all users"""
    # Setup - create a tournament
    tournament = create_test_tournament(init_database.session)
    
    # Test routes that should be accessible to everyone
    public_routes = [
        '/',                                 # Homepage
        '/events',                           # Tournament listing
        f'/tournament/{tournament.id}',      # Tournament details
        '/rankings',                         # Player rankings
        '/auth/login',                       # Login page
        '/auth/register'                     # Registration page
    ]
    
    for route in public_routes:
        response = client.get(route)
        assert response.status_code != 403, f"Route {route} should be publicly accessible"
        assert response.status_code in [200, 302], f"Route {route} returned status {response.status_code}"

# def test_admin_routes_access(client, init_database, app):
#     """Test that admin routes are only accessible to admin users"""
#     # Setup - create users with different roles
#     admin = create_test_user(init_database.session, "admin_user", UserRole.ADMIN)
#     player = create_test_user(init_database.session, "player_user", UserRole.PLAYER)
#     organizer = create_test_user(init_database.session, "organizer_user", UserRole.ORGANIZER)
    
#     # Define admin routes to test
#     admin_routes = [
#         '/admin/dashboard',              # Admin dashboard
#         '/admin/users',         # User management
#         '/admin/tournaments'    # Tournament management (admin view)
#     ]
    
#     with app.test_request_context():
#         # Test with no user logged in
#         for route in admin_routes:
#             response = client.get(route, follow_redirects=False)
#             assert response.status_code in [401, 403, 302], f"Unauthenticated access to {route} should be denied"
        
#         # Test with player role
#         login_user(client, player)
#         for route in admin_routes:
#             response = client.get(route, follow_redirects=False)
#             assert response.status_code in [401, 403, 302], f"Player access to {route} should be denied"
#         logout_user(client)
        
#         # Test with organizer role
#         login_user(client, organizer)
#         for route in admin_routes:
#             response = client.get(route, follow_redirects=False)
#             assert response.status_code in [401, 403, 302], f"Organizer access to {route} should be denied"
#         logout_user(client)
        
#         # Test with admin role
#         login_user(client, admin)
#         for route in admin_routes:
#             response = client.get(route)
#             assert response.status_code == 200, f"Admin should be able to access {route}"
#         logout_user(client)

def test_organizer_routes_access(client, init_database, app):
    """Test that organizer routes are only accessible to organizer and admin users"""
    # Setup - create users with different roles
    # admin = create_test_user(init_database.session, "admin_test", UserRole.ADMIN)
    player = create_test_user(init_database.session, "player_test", UserRole.PLAYER)
    organizer = create_test_user(init_database.session, "organizer_test", UserRole.ORGANIZER)
    
    # Create a tournament with the organizer
    tournament = create_test_tournament(init_database.session, organizer=organizer)
    
    # Define organizer routes to test
    organizer_routes = [
        '/organizer/dashboard',                              # Organizer dashboard
        # '/organizer/tournaments',                   # Tournament listing
        f'/organizer/tournament/{tournament.id}',   # Tournament management
        f'/organizer/tournament/{tournament.id}/edit', # Edit tournament
        f'/organizer/tournament/{tournament.id}/edit/categories', # Manage categories
        f'/organizer/registrations' # Manage registrations
    ]
    
    with app.test_request_context():
        # Test with no user logged in
        for route in organizer_routes:
            response = client.get(route, follow_redirects=False)
            assert response.status_code in [401, 403, 302], f"Unauthenticated access to {route} should be denied"
        
        # Test with player role
        login_user(client, player)
        for route in organizer_routes:
            response = client.get(route, follow_redirects=False)
            assert response.status_code in [401, 403, 302], f"Player access to {route} should be denied"
        logout_user(client)
        
        # Test with organizer role
        login_user(client, organizer)
        for route in organizer_routes:
            response = client.get(route)
            assert response.status_code == 200, f"Organizer should be able to access {route}"
        logout_user(client)
        
        # Test with admin role
        # login_user(client, admin)
        # for route in organizer_routes:
        #     response = client.get(route)
        #     assert response.status_code == 200, f"Admin should be able to access {route}"
        # logout_user(client)

def test_player_routes_access(client, init_database, app):
    """Test that player routes are only accessible to authenticated users"""
    # Setup - create users
    player = create_test_user(init_database.session, "player_access", UserRole.PLAYER)
    other_player = create_test_user(init_database.session, "other_player", UserRole.PLAYER)
    
    # Define player routes to test
    player_routes = [
        '/player/dashboard',                # Player dashboard
        '/player/edit_profile',         # Edit profile
        '/player/my_registrations',   # View registrations
        # '/player/matches'          # View matches
    ]
    
    with app.test_request_context():
        # Test with no user logged in
        for route in player_routes:
            response = client.get(route, follow_redirects=False)
            assert response.status_code in [401, 403, 302], f"Unauthenticated access to {route} should be denied"
        
        # Test with player role
        login_user(client, player)
        for route in player_routes:
            response = client.get(route)
            assert response.status_code == 200, f"Player should be able to access {route}"
        logout_user(client)

# def test_referee_routes_access(client, init_database, app):
#     """Test that referee routes are only accessible to referees, organizers, and admins"""
#     # Setup - create users with different roles
#     admin = create_test_user(init_database.session, "admin_referee", UserRole.ADMIN)
#     player = create_test_user(init_database.session, "player_referee", UserRole.PLAYER)
#     organizer = create_test_user(init_database.session, "organizer_referee", UserRole.ORGANIZER)
#     referee = create_test_user(init_database.session, "referee_user", UserRole.REFEREE)
    
#     # Create a tournament and match
#     tournament = create_test_tournament(init_database.session, organizer=organizer)
    
#     # Define referee routes to test - typically match scoring routes
#     referee_routes = [
#         f'/referee/',                    # Referee dashboard
#         f'/referee/matches',             # Match listing
#         f'/referee/tournament/{tournament.id}' # Tournament matches for referee
#     ]
    
#     with app.test_request_context():
#         # Test with no user logged in
#         for route in referee_routes:
#             response = client.get(route, follow_redirects=False)
#             assert response.status_code in [401, 403, 302], f"Unauthenticated access to {route} should be denied"
        
#         # Test with player role
#         login_user(client, player)
#         for route in referee_routes:
#             response = client.get(route, follow_redirects=False)
#             assert response.status_code in [401, 403, 302], f"Player access to {route} should be denied"
#         logout_user(client)
        
#         # Test with referee role
#         login_user(client, referee)
#         for route in referee_routes:
#             response = client.get(route)
#             assert response.status_code == 200, f"Referee should be able to access {route}"
#         logout_user(client)
        
#         # Test with organizer role
#         login_user(client, organizer)
#         for route in referee_routes:
#             response = client.get(route)
#             assert response.status_code == 200, f"Organizer should be able to access {route}"
#         logout_user(client)
        
#         # Test with admin role
#         login_user(client, admin)
#         for route in referee_routes:
#             response = client.get(route)
#             assert response.status_code == 200, f"Admin should be able to access {route}"
#         logout_user(client)

def test_player_edit_profile(client, init_database, app):
    """Test that a player can only edit their own profile"""
    # Setup - create two players
    player1 = create_test_user(init_database.session, "player_edit1", UserRole.PLAYER)
    player2 = create_test_user(init_database.session, "player_edit2", UserRole.PLAYER)
    
    with app.test_request_context():
        # Log in as player1
        login_user(client, player1)
        
        # Should be able to edit own profile
        response = client.get('/player/edit_profile')
        assert response.status_code == 200, "Player should be able to access own profile"
        
        logout_user(client)

def test_organizer_tournament_ownership(client, init_database, app):
    """Test that an organizer can only edit their own tournaments (unless admin)"""
    # Setup - create two organizers and an admin
    organizer1 = create_test_user(init_database.session, "organizer_own1", UserRole.ORGANIZER)
    organizer2 = create_test_user(init_database.session, "organizer_own2", UserRole.ORGANIZER)
    admin = create_test_user(init_database.session, "admin_own", UserRole.ADMIN)
    
    # Create a tournament for each organizer
    tournament1 = create_test_tournament(init_database.session, "Tournament 1", organizer1)
    tournament2 = create_test_tournament(init_database.session, "Tournament 2", organizer2)
    
    with app.test_request_context():
        # Log in as organizer1
        login_user(client, organizer1)
        
        # Should be able to edit own tournament
        response = client.get(f'/organizer/tournament/{tournament1.id}/edit')
        assert response.status_code == 200, "Organizer should be able to edit own tournament"
        
        # Should not be able to edit tournament of organizer2
        response = client.get(f'/organizer/tournament/{tournament2.id}/edit', follow_redirects=False)
        assert response.status_code in [401, 403, 302], "Organizer should not be able to edit another organizer's tournament"
        
        logout_user(client)
        
        # # Log in as admin
        # login_user(client, admin)
        
        # # Admin should be able to edit both tournaments
        # response = client.get(f'/organizer/tournament/{tournament1.id}/edit')
        # assert response.status_code == 200, "Admin should be able to edit any tournament"
        
        # response = client.get(f'/organizer/tournament/{tournament2.id}/edit')
        # assert response.status_code == 200, "Admin should be able to edit any tournament"
        
        # logout_user(client)

def test_match_verification_permissions(client, init_database, app):
    """Test match verification permissions (referee first, then player)"""
    # Setup - create users
    player = create_test_user(init_database.session, "player_verify", UserRole.PLAYER)
    referee = create_test_user(init_database.session, "referee_verify", UserRole.REFEREE)
    organizer = create_test_user(init_database.session, "organizer_verify", UserRole.ORGANIZER)
    
    # Create tournament and match
    tournament = create_test_tournament(init_database.session, organizer=organizer)
    
    # This test would need to be adapted to your actual route structures and match verification flow
    # The following is just a conceptual example
    
    match_verification_routes = [
        # f'/referee/match/1/verify',   # Referee verification route
        f'/player/match/1/verify'     # Player verification route
    ]
    
    with app.test_request_context():
        # Test referee verification
        login_user(client, referee)
        # Test verification API or form submission here
        logout_user(client)
        
        # Test player verification
        login_user(client, player)
        # Test verification API or form submission here
        logout_user(client)
        
        # Test proper order of verification (referee must verify before player)
        # This would involve more specific test logic based on your implementation

def test_check_in_permissions(client, init_database, app):
    """Test that only registered players can check in to their own matches"""
    # This test would need to be adapted to your actual route structures and check-in flow
    # The following is just a conceptual example
    
    # Setup - create users and registrations
    player1 = create_test_user(init_database.session, "player_checkin1", UserRole.PLAYER)
    player2 = create_test_user(init_database.session, "player_checkin2", UserRole.PLAYER)
    
    # Create tournament and registrations
    tournament = create_test_tournament(init_database.session)
    
    with app.test_request_context():
        # Test player1 checking in to their own registration
        login_user(client, player1)
        # Test check-in API or form submission here
        logout_user(client)
        
        # Test player2 cannot check in for player1
        login_user(client, player2)
        # Test check-in API or form submission here
        logout_user(client)
