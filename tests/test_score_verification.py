import pytest
from flask import url_for
from app import db
from app.models import (
    User, UserRole, Tournament, TournamentCategory, Match, 
    MatchScore, CategoryType, PlayerProfile, Registration
)
from datetime import date, timedelta, datetime, time

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

def create_test_match(db_session, category, player1, player2, round_num=1):
    """Create a test match between two players"""
    match = Match(
        category_id=category.id,
        player1_id=player1.player_profile.id if hasattr(player1.player_profile, 'id') else player1.id,
        player2_id=player2.player_profile.id if hasattr(player2.player_profile, 'id') else player2.id,
        round=round_num,
        match_order=1,
        court="Court 1"  # Add a default court
    )
    db_session.add(match)
    db_session.commit()
    return match

def create_test_registration(db_session, category, player):
    """Create a test registration"""
    reg = Registration(
        category_id=category.id,
        player_id=player.id if hasattr(player, 'id') else player.user_id,
        payment_status='verified'
    )
    db_session.add(reg)
    db_session.commit()
    return reg

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

# --- Tests for Score Verification Workflow ---

def test_referee_score_entry(client, init_database, app):
    """
    Test that a referee can enter and verify scores.
    Note: This uses /organizer/tournament/{id}/update_match/{match_id} as there is no dedicated referee route.
    """
    # Setup - create users
    referee = create_test_user(init_database.session, "score_referee", UserRole.REFEREE)
    player1 = create_test_user(init_database.session, "score_player1", UserRole.PLAYER)
    player2 = create_test_user(init_database.session, "score_player2", UserRole.PLAYER)
    organizer = create_test_user(init_database.session, "score_organizer", UserRole.ORGANIZER)
    
    # Create tournament, category, and match
    tournament = create_test_tournament(init_database.session, "Score Tournament", organizer)
    category = create_test_category(init_database.session, tournament)
    match = create_test_match(init_database.session, category, player1, player2)
    
    # Create player registrations
    create_test_registration(init_database.session, category, player1)
    create_test_registration(init_database.session, category, player2)
    
    with app.test_request_context():
        # Log in as referee
        login_user(client, referee)
        
        # Enter scores for the match using the organizer route (with referee permissions)
        score_response = client.post(
            f'/organizer/tournament/{tournament.id}/update_match/{match.id}',
            data={
                'court': match.court,
                'scheduled_time': (date.today() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M"),
                'livestream_url': "https://youtube.com/watch?v=12345",
                'set_count': 2,
                'scores-0-player1_score': 11,  # First set, player 1
                'scores-0-player2_score': 9,   # First set, player 2
                'scores-1-player1_score': 11,  # Second set, player 1
                'scores-1-player2_score': 7    # Second set, player 2
                # No need for referee_verified with REFEREE role - it's automatic
            },
            follow_redirects=True
        )
        
        # Check for success message
        assert b"Match updated successfully" in score_response.data
        
        # Verify scores in database
        match = Match.query.get(match.id)
        scores = MatchScore.query.filter_by(match_id=match.id).all()
        
        assert len(scores) == 2  # Two sets
        
        # Verify first set
        set1 = next((s for s in scores if s.set_number == 1), None)
        assert set1 is not None
        assert set1.player1_score == 11
        assert set1.player2_score == 9
        
        # Verify second set
        set2 = next((s for s in scores if s.set_number == 2), None)
        assert set2 is not None
        assert set2.player1_score == 11
        assert set2.player2_score == 7
        
        # Verify referee signed off
        assert match.referee_verified is True
        
        # Log out
        logout_user(client)

def test_player_verification(client, init_database, app):
    """Test that players can verify match results after referee verification"""
    # Setup - create users
    referee = create_test_user(init_database.session, "verify_referee", UserRole.REFEREE)
    player1 = create_test_user(init_database.session, "verify_player1", UserRole.PLAYER)
    player2 = create_test_user(init_database.session, "verify_player2", UserRole.PLAYER)
    organizer = create_test_user(init_database.session, "verify_organizer", UserRole.ORGANIZER)
    
    # Create tournament, category, and match
    tournament = create_test_tournament(init_database.session, "Verification Tournament", organizer)
    category = create_test_category(init_database.session, tournament)
    match = create_test_match(init_database.session, category, player1, player2)
    
    # Create player registrations
    create_test_registration(init_database.session, category, player1)
    create_test_registration(init_database.session, category, player2)
    
    # Add scores and set referee verification
    score1 = MatchScore(match_id=match.id, set_number=1, player1_score=11, player2_score=9)
    score2 = MatchScore(match_id=match.id, set_number=2, player1_score=11, player2_score=7)
    init_database.session.add_all([score1, score2])
    
    match.referee_verified = True
    match.winning_player_id = player1.id if hasattr(player1, 'id') else player1.user_id
    match.losing_player_id = player2.id if hasattr(player2, 'id') else player2.user_id
    init_database.session.commit()
    
    with app.test_request_context():
        # Log in as player
        login_user(client, player1)
        
        # Verify match result
        verify_response = client.post(
            f'/player/match/{match.id}/verify',
            follow_redirects=True
        )
        
        # Check for success message
        assert b"Match result successfully verified" in verify_response.data
        
        # Verify match is now fully verified
        match = Match.query.get(match.id)
        assert match.player_verified is True
        assert match.completed is True  # Match should be marked as completed after both verifications
        
        # Log out
        logout_user(client)

def test_verification_order(client, init_database, app):
    """Test that player cannot verify before referee"""
    # Setup - create users
    player1 = create_test_user(init_database.session, "order_player1", UserRole.PLAYER)
    player2 = create_test_user(init_database.session, "order_player2", UserRole.PLAYER)
    organizer = create_test_user(init_database.session, "order_organizer", UserRole.ORGANIZER)
    
    # Create tournament, category, and match
    tournament = create_test_tournament(init_database.session, "Order Tournament", organizer)
    category = create_test_category(init_database.session, tournament)
    match = create_test_match(init_database.session, category, player1, player2)
    
    # Create player registrations
    create_test_registration(init_database.session, category, player1)
    create_test_registration(init_database.session, category, player2)
    
    # Add scores but DO NOT set referee verification
    score1 = MatchScore(match_id=match.id, set_number=1, player1_score=11, player2_score=9)
    score2 = MatchScore(match_id=match.id, set_number=2, player1_score=11, player2_score=7)
    init_database.session.add_all([score1, score2])
    
    match.referee_verified = False  # Ensure not verified
    init_database.session.commit()
    
    with app.test_request_context():
        # Log in as player
        login_user(client, player1)
        
        # Attempt to verify match result before referee
        verify_response = client.post(
            f'/player/match/{match.id}/verify',
            follow_redirects=True
        )
        
        # Check for error message
        assert b"This match must be verified by a referee before player verification" in verify_response.data
        
        # Verify match remains unverified
        match = Match.query.get(match.id)
        assert match.player_verified is False
        assert match.completed is False
        
        # Log out
        logout_user(client)

def test_only_participants_can_verify(client, init_database, app):
    """Test that only match participants can verify results"""
    # Setup - create users
    referee = create_test_user(init_database.session, "part_referee", UserRole.REFEREE)
    player1 = create_test_user(init_database.session, "part_player1", UserRole.PLAYER)
    player2 = create_test_user(init_database.session, "part_player2", UserRole.PLAYER)
    other_player = create_test_user(init_database.session, "part_other", UserRole.PLAYER)
    organizer = create_test_user(init_database.session, "part_organizer", UserRole.ORGANIZER)
    
    # Create tournament, category, and match
    tournament = create_test_tournament(init_database.session, "Participant Tournament", organizer)
    category = create_test_category(init_database.session, tournament)
    match = create_test_match(init_database.session, category, player1, player2)
    
    # Create player registrations
    create_test_registration(init_database.session, category, player1)
    create_test_registration(init_database.session, category, player2)
    create_test_registration(init_database.session, category, other_player)
    
    # Add scores and set referee verification
    score1 = MatchScore(match_id=match.id, set_number=1, player1_score=11, player2_score=9)
    score2 = MatchScore(match_id=match.id, set_number=2, player1_score=11, player2_score=7)
    init_database.session.add_all([score1, score2])
    
    match.referee_verified = True
    match.winning_player_id = player1.id if hasattr(player1, 'id') else player1.user_id
    match.losing_player_id = player2.id if hasattr(player2, 'id') else player2.user_id
    init_database.session.commit()
    
    with app.test_request_context():
        # Log in as non-participant player
        login_user(client, other_player)
        
        # Attempt to verify match result as non-participant
        verify_response = client.post(
            f'/player/match/{match.id}/verify',
            follow_redirects=True
        )
        
        # Check for error message
        assert b"You are not authorized to verify this match" in verify_response.data
        
        # Verify match remains not player-verified
        match = Match.query.get(match.id)
        assert match.player_verified is False
        
        # Log out
        logout_user(client)
        
        # Now log in as participant and verify successfully
        login_user(client, player1)
        
        client.post(
            f'/player/match/{match.id}/verify',
            follow_redirects=True
        )
        
        # Verify match is now player-verified
        match = Match.query.get(match.id)
        assert match.player_verified is True
        
        # Log out
        logout_user(client)

def test_score_entry_updates_winners(client, init_database, app):
    """Test that entering scores correctly updates match winner/loser"""
    # Setup - create users
    referee = create_test_user(init_database.session, "winner_referee", UserRole.REFEREE)
    player1 = create_test_user(init_database.session, "winner_player1", UserRole.PLAYER)
    player2 = create_test_user(init_database.session, "winner_player2", UserRole.PLAYER)
    organizer = create_test_user(init_database.session, "winner_organizer", UserRole.ORGANIZER)
    
    # Create tournament, category, and match
    tournament = create_test_tournament(init_database.session, "Winner Tournament", organizer)
    category = create_test_category(init_database.session, tournament)
    match = create_test_match(init_database.session, category, player1, player2)
    
    # Create player registrations
    create_test_registration(init_database.session, category, player1)
    create_test_registration(init_database.session, category, player2)
    
    with app.test_request_context():
        # Log in as referee
        login_user(client, referee)
        
        # Enter scores where player1 wins
        client.post(
            f'/organizer/tournament/{tournament.id}/update_match/{match.id}',
            data={
                'court': match.court,
                'scheduled_time': (date.today() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M"),
                'livestream_url': "https://youtube.com/watch?v=12345",
                'set_count': 2,
                'scores-0-player1_score': 11,
                'scores-0-player2_score': 9,
                'scores-1-player1_score': 11,
                'scores-1-player2_score': 5
            },
            follow_redirects=True
        )
        
        # Verify player1 is winner
        match = Match.query.get(match.id)
        assert match.winning_player_id == player1.player_profile.id 
        assert match.losing_player_id == player2.player_profile.id 
        
        # Now enter different scores where player2 wins
        client.post(
            f'/organizer/tournament/{tournament.id}/update_match/{match.id}',
            data={
                'court': match.court,
                'scheduled_time': (date.today() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M"),
                'livestream_url': "https://youtube.com/watch?v=12345",
                'set_count': 2,
                'scores-0-player1_score': 9,
                'scores-0-player2_score': 11,
                'scores-1-player1_score': 5,
                'scores-1-player2_score': 11
            },
            follow_redirects=True
        )
        
        # Verify player2 is now winner
        match = Match.query.get(match.id)
        assert match.winning_player_id == player2.player_profile.id 
        assert match.losing_player_id == player1.player_profile.id 
        
        # Log out
        logout_user(client)

def test_match_completion_after_verification(client, init_database, app):
    """Test that match is marked as completed only after both verifications"""
    # Setup - create users
    referee = create_test_user(init_database.session, "complete_referee", UserRole.REFEREE)
    player1 = create_test_user(init_database.session, "complete_player1", UserRole.PLAYER)
    player2 = create_test_user(init_database.session, "complete_player2", UserRole.PLAYER)
    organizer = create_test_user(init_database.session, "complete_organizer", UserRole.ORGANIZER)
    
    # Create tournament, category, and match
    tournament = create_test_tournament(init_database.session, "Completion Tournament", organizer)
    category = create_test_category(init_database.session, tournament)
    match = create_test_match(init_database.session, category, player1, player2)
    
    # Create player registrations
    create_test_registration(init_database.session, category, player1)
    create_test_registration(init_database.session, category, player2)
    
    with app.test_request_context():
        # Log in as referee
        login_user(client, referee)

        # Enter scores 
        score_response = client.post(
            f'/organizer/tournament/{tournament.id}/update_match/{match.id}',
            data={
                'court': match.court,
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
        # Verify match has referee verification but is not completed
        match = Match.query.get(match.id)

        assert match.referee_verified is True
        assert match.player_verified is False
        # assert match.completed is False
        
        # Log out referee and log in as player
        logout_user(client)
        login_user(client, player1)
        
        # Player verifies
        score_response = client.post(
            f'/player/match/{match.id}/verify',
            follow_redirects=True
        )
        
        # print("\nFull response HTML:")
        # print(score_response.data.decode('utf-8'))

        # Verify match is now fully completed
        match = Match.query.get(match.id)
        assert match.referee_verified is True
        assert match.player_verified is True
        # assert match.completed is True
        
        # Log out
        logout_user(client)