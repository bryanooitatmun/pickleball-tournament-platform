import pytest
from app import db
from app.models import Tournament, TournamentCategory, Match, Team, Registration, User, PlayerProfile, TournamentFormat, MatchStage, MatchScore, CategoryType, TournamentStatus
from app.services.placing_service import PlacingService
from datetime import date, timedelta

# Helper functions to create test data
def create_test_tournament(db_session, format=TournamentFormat.SINGLE_ELIMINATION, status=TournamentStatus.UPCOMING):
    """Create a test tournament with the specified format and status"""
    t = Tournament(
        name="Test Tournament",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=2),
        registration_deadline=date.today() - timedelta(days=1),
        format=format,
        status=status
    )
    db_session.add(t)
    db_session.commit()
    return t

def create_test_category(db_session, tournament, category_type=CategoryType.MENS_SINGLES, points_awarded=100):
    """Create a test category with the specified tournament and category type"""
    c = TournamentCategory(
        tournament_id=tournament.id,
        category_type=category_type,
        name=category_type.value,
        max_participants=16,
        points_awarded=points_awarded,
        prize_money=1000.0
    )
    db_session.add(c)
    db_session.commit()
    return c

def create_test_player(db_session, suffix):
    """Create a test player with the specified suffix"""
    u = User(username=f"player{suffix}", email=f"player{suffix}@test.com")
    u.set_password("password")
    p = PlayerProfile(user=u, full_name=f"Player {suffix}")
    db_session.add(u)
    db_session.commit()
    return p

def create_test_team(db_session, player1, player2, category):
    """Create a test team with the specified players and category"""
    team = Team(
        player1_id=player1.user_id,
        player2_id=player2.user_id,
        category_id=category.id
    )
    db_session.add(team)
    db_session.commit()
    return team

def create_knockout_match(db_session, category, round_num, match_order=1, is_doubles=False, 
                          player1=None, player2=None, team1=None, team2=None,
                          winner_id=None, loser_id=None, completed=True):
    """Create a knockout match with the specified parameters"""
    match = Match(
        category_id=category.id,
        round=round_num,
        match_order=match_order,
        stage=MatchStage.KNOCKOUT,
        completed=completed
    )
    
    if is_doubles:
        match.team1_id = team1.id if team1 else None
        match.team2_id = team2.id if team2 else None
        match.winning_team_id = winner_id
        match.losing_team_id = loser_id
    else:
        match.player1_id = player1.user_id if player1 else None
        match.player2_id = player2.user_id if player2 else None
        match.winning_player_id = winner_id
        match.losing_player_id = loser_id
    
    db_session.add(match)
    db_session.commit()
    
    # Add scores if match is completed
    if completed:
        score1 = MatchScore(match_id=match.id, set_number=1, player1_score=11, player2_score=5)
        score2 = MatchScore(match_id=match.id, set_number=2, player1_score=11, player2_score=7)
        db_session.add_all([score1, score2])
        db_session.commit()
    
    return match

# --- Tests for PlacingService ---

def test_get_placings_singles_tournament_not_completed(init_database):
    """Test that get_placings returns empty list if tournament is not completed"""
    # Setup
    tournament = create_test_tournament(init_database.session, status=TournamentStatus.ONGOING)
    category = create_test_category(init_database.session, tournament)
    
    # Test
    placings = PlacingService.get_placings(category.id)
    
    # Assert
    assert placings == []

def test_get_placings_singles_completed_tournament(init_database):
    """Test get_placings for a singles tournament with proper setup of matches"""
    # Setup
    tournament = create_test_tournament(init_database.session, status=TournamentStatus.COMPLETED)
    category = create_test_category(init_database.session, tournament)
    
    # Create 4 players
    p1 = create_test_player(init_database.session, "1")
    p2 = create_test_player(init_database.session, "2")
    p3 = create_test_player(init_database.session, "3")
    p4 = create_test_player(init_database.session, "4")
    
    # Create semifinal matches
    semi1 = create_knockout_match(
        init_database.session, 
        category, 
        round_num=2,  # Semifinal
        match_order=1,
        player1=p1,
        player2=p2,
        winner_id=p1.user_id,
        loser_id=p2.user_id
    )
    
    semi2 = create_knockout_match(
        init_database.session, 
        category, 
        round_num=2,  # Semifinal
        match_order=2,
        player1=p3,
        player2=p4,
        winner_id=p3.user_id,
        loser_id=p4.user_id
    )
    
    # Create finals match
    final = create_knockout_match(
        init_database.session, 
        category, 
        round_num=1,  # Final
        match_order=1,
        player1=p1,
        player2=p3,
        winner_id=p1.user_id,
        loser_id=p3.user_id
    )
    
    # Create 3rd place playoff
    playoff = create_knockout_match(
        init_database.session, 
        category, 
        round_num=1.5,  # Playoff
        match_order=1,
        player1=p2,
        player2=p4,
        winner_id=p2.user_id,
        loser_id=p4.user_id
    )
    playoff.stage = MatchStage.PLAYOFF
    init_database.session.commit()
    
    # Test
    placings = PlacingService.get_placings(category.id)
    
    # Assert
    assert len(placings) == 4  # 4 players should have placings
    
    # Find placing for each player
    p1_placing = next((p for p in placings if not p['is_team'] and p['participant'].id == p1.user_id), None)
    p2_placing = next((p for p in placings if not p['is_team'] and p['participant'].id == p2.user_id), None)
    p3_placing = next((p for p in placings if not p['is_team'] and p['participant'].id == p3.user_id), None)
    p4_placing = next((p for p in placings if not p['is_team'] and p['participant'].id == p4.user_id), None)
    
    # Check player placings
    assert p1_placing is not None
    assert p1_placing['place'] == 1  # Winner gets 1st place
    assert p1_placing['points'] == category.points_awarded  # Full points
    assert p1_placing['prize'] == category.prize_money * 0.5  # 50% of prize pool
    
    assert p3_placing is not None
    assert p3_placing['place'] == 2  # Runner-up gets 2nd place
    assert p3_placing['points'] == int(category.points_awarded * 0.7)  # 70% of points
    assert p3_placing['prize'] == category.prize_money * 0.25  # 25% of prize pool
    
    assert p2_placing is not None
    assert p2_placing['place'] == 3  # 3rd place playoff winner gets 3rd place
    assert p2_placing['points'] == int(category.points_awarded * 0.5)  # 50% of points
    assert p2_placing['prize'] == category.prize_money * 0.125  # 12.5% of prize pool
    
    assert p4_placing is not None
    assert p4_placing['place'] == 4  # 3rd place playoff loser gets 4th place
    assert p4_placing['points'] == int(category.points_awarded * 0.5)  # 50% of points
    assert p4_placing['prize'] == category.prize_money * 0.125  # 12.5% of prize pool

def test_get_placings_singles_no_playoff(init_database):
    """Test get_placings for a singles tournament without 3rd place playoff match"""
    # Setup
    tournament = create_test_tournament(init_database.session, status=TournamentStatus.COMPLETED)
    category = create_test_category(init_database.session, tournament)
    
    # Create 4 players
    p1 = create_test_player(init_database.session, "a")
    p2 = create_test_player(init_database.session, "b")
    p3 = create_test_player(init_database.session, "c")
    p4 = create_test_player(init_database.session, "d")
    
    # Create semifinal matches
    semi1 = create_knockout_match(
        init_database.session, 
        category, 
        round_num=2,
        match_order=1,
        player1=p1,
        player2=p2,
        winner_id=p1.user_id,
        loser_id=p2.user_id
    )
    
    semi2 = create_knockout_match(
        init_database.session, 
        category, 
        round_num=2,
        match_order=2,
        player1=p3,
        player2=p4,
        winner_id=p3.user_id,
        loser_id=p4.user_id
    )
    
    # Create finals match
    final = create_knockout_match(
        init_database.session, 
        category, 
        round_num=1,
        match_order=1,
        player1=p1,
        player2=p3,
        winner_id=p1.user_id,
        loser_id=p3.user_id
    )
    
    # No playoff match
    
    # Test
    placings = PlacingService.get_placings(category.id)
    
    # Assert
    assert len(placings) == 4  # 4 players should have placings
    
    # Find placing for each player
    p1_placing = next((p for p in placings if not p['is_team'] and p['participant'].id == p1.user_id), None)
    p2_placing = next((p for p in placings if not p['is_team'] and p['participant'].id == p2.user_id), None)
    p3_placing = next((p for p in placings if not p['is_team'] and p['participant'].id == p3.user_id), None)
    p4_placing = next((p for p in placings if not p['is_team'] and p['participant'].id == p4.user_id), None)
    
    # Check winner and runner-up
    assert p1_placing is not None
    assert p1_placing['place'] == 1
    
    assert p3_placing is not None
    assert p3_placing['place'] == 2
    
    # Check semifinalists (should both be 3rd place without a playoff)
    assert p2_placing is not None
    assert p2_placing['place'] == 3  # Tied for 3rd without playoff
    
    assert p4_placing is not None
    assert p4_placing['place'] == 3  # Tied for 3rd without playoff

def test_get_placings_singles_larger_tournament(init_database):
    """Test get_placings for a larger singles tournament with quarterfinals"""
    # Setup
    tournament = create_test_tournament(init_database.session, status=TournamentStatus.COMPLETED)
    category = create_test_category(init_database.session, tournament)
    
    # Create 8 players
    players = [create_test_player(init_database.session, f"player{i}") for i in range(1, 9)]
    
    # Create quarterfinal matches (round 3)
    qf1 = create_knockout_match(
        init_database.session, category, round_num=3, match_order=1,
        player1=players[0], player2=players[1], winner_id=players[0].user_id, loser_id=players[1].user_id
    )
    qf2 = create_knockout_match(
        init_database.session, category, round_num=3, match_order=2,
        player1=players[2], player2=players[3], winner_id=players[2].user_id, loser_id=players[3].user_id
    )
    qf3 = create_knockout_match(
        init_database.session, category, round_num=3, match_order=3,
        player1=players[4], player2=players[5], winner_id=players[4].user_id, loser_id=players[5].user_id
    )
    qf4 = create_knockout_match(
        init_database.session, category, round_num=3, match_order=4,
        player1=players[6], player2=players[7], winner_id=players[6].user_id, loser_id=players[7].user_id
    )
    
    # Create semifinal matches (round 2)
    sf1 = create_knockout_match(
        init_database.session, category, round_num=2, match_order=1,
        player1=players[0], player2=players[2], winner_id=players[0].user_id, loser_id=players[2].user_id
    )
    sf2 = create_knockout_match(
        init_database.session, category, round_num=2, match_order=2,
        player1=players[4], player2=players[6], winner_id=players[4].user_id, loser_id=players[6].user_id
    )
    
    # Create final match (round 1)
    final = create_knockout_match(
        init_database.session, category, round_num=1, match_order=1,
        player1=players[0], player2=players[4], winner_id=players[0].user_id, loser_id=players[4].user_id
    )
    
    # Test
    placings = PlacingService.get_placings(category.id)
    
    # Assert
    assert len(placings) == 8  # All 8 players should have placings
    
    # Group placings by place
    placings_by_place = {}
    for placing in placings:
        if placing['place'] not in placings_by_place:
            placings_by_place[placing['place']] = []
        placings_by_place[placing['place']].append(placing)
    
    # Check counts for each placing
    assert len(placings_by_place[1]) == 1  # 1 winner
    assert len(placings_by_place[2]) == 1  # 1 runner-up
    assert len(placings_by_place[3]) == 2  # 2 semifinal losers
    assert len(placings_by_place[5]) == 4  # 4 quarterfinal losers
    
    # Check 1st place (winner)
    winner = placings_by_place[1][0]
    assert not winner['is_team']
    assert winner['participant'].id == players[0].user_id
    assert winner['points'] == category.points_awarded
    assert winner['prize'] == category.prize_money * 0.5
    
    # Check 2nd place (runner-up)
    runner_up = placings_by_place[2][0]
    assert not runner_up['is_team']
    assert runner_up['participant'].id == players[4].user_id
    assert runner_up['points'] == int(category.points_awarded * 0.7)
    assert runner_up['prize'] == category.prize_money * 0.25
    
    # Check quarterfinal losers (should be 5th place)
    qf_losers_ids = [players[1].user_id, players[3].user_id, players[5].user_id, players[7].user_id]
    for placing in placings_by_place[5]:
        assert not placing['is_team']
        assert placing['participant'].id in qf_losers_ids
        assert placing['points'] == int(category.points_awarded * 0.25)
        assert placing['prize'] == category.prize_money * 0.0625

def test_get_placings_doubles_tournament(init_database):
    """Test get_placings for a doubles tournament"""
    # Setup
    tournament = create_test_tournament(init_database.session, status=TournamentStatus.COMPLETED)
    category = create_test_category(init_database.session, tournament, category_type=CategoryType.MENS_DOUBLES)
    
    # Create 8 players (for 4 teams)
    players = [create_test_player(init_database.session, f"dbl{i}") for i in range(1, 9)]
    
    # Create 4 teams
    team1 = create_test_team(init_database.session, players[0], players[1], category)
    team2 = create_test_team(init_database.session, players[2], players[3], category)
    team3 = create_test_team(init_database.session, players[4], players[5], category)
    team4 = create_test_team(init_database.session, players[6], players[7], category)
    
    # Create semifinal matches
    semi1 = create_knockout_match(
        init_database.session, category, round_num=2, match_order=1, is_doubles=True,
        team1=team1, team2=team2, winner_id=team1.id, loser_id=team2.id
    )
    
    semi2 = create_knockout_match(
        init_database.session, category, round_num=2, match_order=2, is_doubles=True,
        team1=team3, team2=team4, winner_id=team3.id, loser_id=team4.id
    )
    
    # Create final match
    final = create_knockout_match(
        init_database.session, category, round_num=1, match_order=1, is_doubles=True,
        team1=team1, team2=team3, winner_id=team1.id, loser_id=team3.id
    )
    
    # Test
    placings = PlacingService.get_placings(category.id)
    
    # Assert
    assert len(placings) == 4  # 4 teams should have placings
    
    # Find placing for each team
    t1_placing = next((p for p in placings if p['is_team'] and p['participant'].id == team1.id), None)
    t2_placing = next((p for p in placings if p['is_team'] and p['participant'].id == team2.id), None)
    t3_placing = next((p for p in placings if p['is_team'] and p['participant'].id == team3.id), None)
    t4_placing = next((p for p in placings if p['is_team'] and p['participant'].id == team4.id), None)
    
    # Check team placings
    assert t1_placing is not None
    assert t1_placing['place'] == 1  # Winner gets 1st place
    assert t1_placing['points'] == category.points_awarded  # Full points
    
    assert t3_placing is not None
    assert t3_placing['place'] == 2  # Runner-up gets 2nd place
    assert t3_placing['points'] == int(category.points_awarded * 0.7)  # 70% of points
    
    assert t2_placing is not None
    assert t2_placing['place'] == 3  # Semifinal loser gets tied 3rd place
    assert t2_placing['points'] == int(category.points_awarded * 0.5)  # 50% of points
    
    assert t4_placing is not None
    assert t4_placing['place'] == 3  # Semifinal loser gets tied 3rd place
    assert t4_placing['points'] == int(category.points_awarded * 0.5)  # 50% of points

def test_custom_points_distribution(init_database):
    """Test get_placings with custom points distribution"""
    # Setup
    tournament = create_test_tournament(init_database.session, status=TournamentStatus.COMPLETED)
    category = create_test_category(init_database.session, tournament, points_awarded=200)
    
    # Set custom points distribution
    category.points_distribution = {
        "1": 100,     # 100% for 1st place
        "2": 60,      # 60% for 2nd place
        "3-4": 40,    # 40% for 3rd-4th place
        "5-8": 20     # 20% for 5th-8th place
    }
    init_database.session.commit()
    
    # Create 4 players
    p1 = create_test_player(init_database.session, "cp1")
    p2 = create_test_player(init_database.session, "cp2")
    p3 = create_test_player(init_database.session, "cp3")
    p4 = create_test_player(init_database.session, "cp4")
    
    # Create semifinal matches
    semi1 = create_knockout_match(
        init_database.session, category, round_num=2, match_order=1,
        player1=p1, player2=p2, winner_id=p1.user_id, loser_id=p2.user_id
    )
    
    semi2 = create_knockout_match(
        init_database.session, category, round_num=2, match_order=2,
        player1=p3, player2=p4, winner_id=p3.user_id, loser_id=p4.user_id
    )
    
    # Create final match
    final = create_knockout_match(
        init_database.session, category, round_num=1, match_order=1,
        player1=p1, player2=p3, winner_id=p1.user_id, loser_id=p3.user_id
    )
    
    # Test
    placings = PlacingService.get_placings(category.id)
    
    # Assert
    p1_placing = next((p for p in placings if not p['is_team'] and p['participant'].id == p1.user_id), None)
    p2_placing = next((p for p in placings if not p['is_team'] and p['participant'].id == p2.user_id), None)
    
    # Check points based on custom distribution
    assert p1_placing['points'] == int(category.points_awarded * (100 / 100))  # 100% = 200 points
    assert p2_placing['points'] == int(category.points_awarded * (40 / 100))   # 40% = 80 points

def test_custom_prize_distribution(init_database):
    """Test get_placings with custom prize distribution"""
    # Setup
    tournament = create_test_tournament(init_database.session, status=TournamentStatus.COMPLETED)
    category = create_test_category(init_database.session, tournament, points_awarded=100)
    category.prize_money = 10000.0
    
    # Set custom prize distribution
    category.prize_distribution = {
        "1": 60,      # 60% for 1st place (6000)
        "2": 30,      # 30% for 2nd place (3000)
        "3-4": 5      # 5% each for 3rd-4th place (500 each)
    }
    init_database.session.commit()
    
    # Create 4 players
    p1 = create_test_player(init_database.session, "cpr1")
    p2 = create_test_player(init_database.session, "cpr2")
    p3 = create_test_player(init_database.session, "cpr3")
    p4 = create_test_player(init_database.session, "cpr4")
    
    # Create semifinal matches
    semi1 = create_knockout_match(
        init_database.session, category, round_num=2, match_order=1,
        player1=p1, player2=p2, winner_id=p1.user_id, loser_id=p2.user_id
    )
    
    semi2 = create_knockout_match(
        init_database.session, category, round_num=2, match_order=2,
        player1=p3, player2=p4, winner_id=p3.user_id, loser_id=p4.user_id
    )
    
    # Create final match
    final = create_knockout_match(
        init_database.session, category, round_num=1, match_order=1,
        player1=p1, player2=p3, winner_id=p1.user_id, loser_id=p3.user_id
    )
    
    # Test
    placings = PlacingService.get_placings(category.id)
    
    # Assert
    p1_placing = next((p for p in placings if not p['is_team'] and p['participant'].id == p1.user_id), None)
    p3_placing = next((p for p in placings if not p['is_team'] and p['participant'].id == p3.user_id), None)
    p2_placing = next((p for p in placings if not p['is_team'] and p['participant'].id == p2.user_id), None)
    
    # Check prize money based on custom distribution
    assert p1_placing['prize'] == category.prize_money * (60 / 100)  # 60% = 6000
    assert p3_placing['prize'] == category.prize_money * (30 / 100)  # 30% = 3000
    assert p2_placing['prize'] == category.prize_money * (5 / 100)   # 5% = 500

def test_place_range_helper_method(init_database):
    """Test the _is_in_place_range helper method directly"""
    # Setup - create minimal category just to access the method
    tournament = create_test_tournament(init_database.session)
    category = create_test_category(init_database.session, tournament)
    
    # Test direct place matches
    assert PlacingService._is_in_place_range(1, "1") is True
    assert PlacingService._is_in_place_range(2, "2") is True
    assert PlacingService._is_in_place_range(3, "4") is False
    
    # Test range matches
    assert PlacingService._is_in_place_range(3, "3-4") is True
    assert PlacingService._is_in_place_range(4, "3-4") is True
    assert PlacingService._is_in_place_range(5, "3-4") is False
    assert PlacingService._is_in_place_range(2, "3-4") is False
    assert PlacingService._is_in_place_range(5, "5-8") is True
    assert PlacingService._is_in_place_range(8, "5-8") is True
    assert PlacingService._is_in_place_range(9, "5-8") is False
    
    # Test invalid formats (should safely return False)
    assert PlacingService._is_in_place_range(1, "invalid") is False
    assert PlacingService._is_in_place_range(1, "1-") is False
    assert PlacingService._is_in_place_range(1, "-1") is False
