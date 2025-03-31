import pytest
from app import db
from app.models import Tournament, TournamentCategory, Match, Group, GroupStanding, Team, Registration, User, PlayerProfile, TournamentFormat, MatchStage, MatchScore, CategoryType
from app.services.bracket_service import BracketService
from datetime import date, timedelta

# Helper function to create common test objects
def create_test_tournament(db_session, name="Test Tourney", format=TournamentFormat.SINGLE_ELIMINATION):
    t = Tournament(
        name=name,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=2),
        registration_deadline=date.today() - timedelta(days=1),
        format=format
    )
    db_session.add(t)
    db_session.commit()
    return t

def create_test_category(db_session, tournament, name="Men's Singles", category_type=CategoryType.MENS_SINGLES):
    c = TournamentCategory(
        tournament_id=tournament.id,
        name=name,
        max_participants=16,
        category_type=category_type
    )
    db_session.add(c)
    db_session.commit()
    return c

def create_test_player(db_session, username_suffix):
    u = User(username=f"player{username_suffix}", email=f"player{username_suffix}@test.com")
    u.set_password("password")
    p = PlayerProfile(user=u, full_name=f"Player {username_suffix}")
    db_session.add(u)
    # db_session.add(p) # PlayerProfile is cascaded from User
    db_session.commit()
    return p

def create_test_registration(db_session, category, player):
    r = Registration(
        category_id=category.id,
        player_id=player.user_id, # Use user_id from PlayerProfile
        payment_status='verified'
    )
    db_session.add(r)
    db_session.commit()
    return r

# --- Tests for BracketService ---

# TODO: Add tests for get_bracket_data
# TODO: Add tests for get_group_data
# TODO: Add tests for update_group_standings (complex logic, needs careful setup)
# TODO: Add tests for _process_match_for_standings
# TODO: Add tests for _update_database_standings
# TODO: Add tests for _update_standing_from_match
# TODO: Add tests for _calculate_group_positions

# Example basic test structure (will be expanded)
def test_update_group_standings_one_match(init_database):
    """
    Test group standings update after one completed match.
    """
    # Setup
    tournament = create_test_tournament(init_database.session, format=TournamentFormat.GROUP_KNOCKOUT)
    category = create_test_category(init_database.session, tournament, name="Test Singles", category_type=CategoryType.MENS_SINGLES)
    group = Group(category_id=category.id, name="Group A")
    init_database.session.add(group)
    init_database.session.commit() # Commit group to get its ID

    player1_profile = create_test_player(init_database.session, "1")
    player2_profile = create_test_player(init_database.session, "2")

    reg1 = create_test_registration(init_database.session, category, player1_profile)
    reg2 = create_test_registration(init_database.session, category, player2_profile)

    # Add players to the group standings initially (might be done by registration logic elsewhere, but needed for test)
    standing1 = GroupStanding(group_id=group.id, player_id=player1_profile.user_id)
    standing2 = GroupStanding(group_id=group.id, player_id=player2_profile.user_id)
    init_database.session.add_all([standing1, standing2])
    init_database.session.commit()


    # Create a completed match
    match1 = Match(
        category_id=category.id,
        group_id=group.id,
        player1_id=player1_profile.user_id,
        player2_id=player2_profile.user_id,
        round=0, # Group stage round
        match_order=1,
        stage=MatchStage.GROUP,
        completed=True,
        winning_player_id=player1_profile.user_id, # Player 1 wins
        losing_player_id=player2_profile.user_id
    )
    init_database.session.add(match1)
    init_database.session.commit() # Commit match to get its ID

    # Add scores for the match
    score1 = MatchScore(match_id=match1.id, set_number=1, player1_score=11, player2_score=5)
    score2 = MatchScore(match_id=match1.id, set_number=2, player1_score=11, player2_score=7)
    init_database.session.add_all([score1, score2])
    init_database.session.commit()

    # Call the service method
    standings_list = BracketService.update_group_standings(group.id)

    # Assertions
    assert len(standings_list) == 2

    # Find standings for player 1 and player 2
    p1_standing = next((s for s in standings_list if s.player_id == player1_profile.user_id), None)
    p2_standing = next((s for s in standings_list if s.player_id == player2_profile.user_id), None)

    assert p1_standing is not None
    assert p2_standing is not None

    # Check Player 1 (Winner)
    assert p1_standing.matches_played == 1
    assert p1_standing.matches_won == 1
    assert p1_standing.matches_lost == 0
    assert p1_standing.sets_won == 2
    assert p1_standing.sets_lost == 0
    assert p1_standing.points_won == 22 # 11 + 11
    assert p1_standing.points_lost == 12 # 5 + 7
    assert p1_standing.position == 1 # Should be ranked 1st

    # Check Player 2 (Loser)
    assert p2_standing.matches_played == 1
    assert p2_standing.matches_won == 0
    assert p2_standing.matches_lost == 1
    assert p2_standing.sets_won == 0
    assert p2_standing.sets_lost == 2
    assert p2_standing.points_won == 12 # 5 + 7
    assert p2_standing.points_lost == 22 # 11 + 11
    assert p2_standing.position == 2 # Should be ranked 2nd


def test_update_group_standings_multiple_matches(init_database):
    """
    Test group standings update after multiple completed matches involving 3 players.
    P1 beats P2
    P2 beats P3
    P1 beats P3
    Expected order: P1 (2-0), P2 (1-1), P3 (0-2)
    """
    # Setup
    tournament = create_test_tournament(init_database.session, format=TournamentFormat.GROUP_KNOCKOUT)
    category = create_test_category(init_database.session, tournament, name="Test Singles Multi", category_type=CategoryType.MENS_SINGLES)
    group = Group(category_id=category.id, name="Group B")
    init_database.session.add(group)
    init_database.session.commit()

    p1 = create_test_player(init_database.session, "m1")
    p2 = create_test_player(init_database.session, "m2")
    p3 = create_test_player(init_database.session, "m3")

    reg1 = create_test_registration(init_database.session, category, p1)
    reg2 = create_test_registration(init_database.session, category, p2)
    reg3 = create_test_registration(init_database.session, category, p3)

    # Add initial standings
    s1 = GroupStanding(group_id=group.id, player_id=p1.user_id)
    s2 = GroupStanding(group_id=group.id, player_id=p2.user_id)
    s3 = GroupStanding(group_id=group.id, player_id=p3.user_id)
    init_database.session.add_all([s1, s2, s3])
    init_database.session.commit()

    # --- Match 1: P1 beats P2 (11-5, 11-7) ---
    match1 = Match(category_id=category.id, group_id=group.id, player1_id=p1.user_id, player2_id=p2.user_id, round=0, match_order=1, stage=MatchStage.GROUP, completed=True, winning_player_id=p1.user_id, losing_player_id=p2.user_id)
    init_database.session.add(match1)
    init_database.session.commit()
    score1_1 = MatchScore(match_id=match1.id, set_number=1, player1_score=11, player2_score=5)
    score1_2 = MatchScore(match_id=match1.id, set_number=2, player1_score=11, player2_score=7)
    init_database.session.add_all([score1_1, score1_2])
    init_database.session.commit()

    # --- Match 2: P2 beats P3 (11-8, 11-9) ---
    match2 = Match(category_id=category.id, group_id=group.id, player1_id=p2.user_id, player2_id=p3.user_id, round=0, match_order=2, stage=MatchStage.GROUP, completed=True, winning_player_id=p2.user_id, losing_player_id=p3.user_id)
    init_database.session.add(match2)
    init_database.session.commit()
    score2_1 = MatchScore(match_id=match2.id, set_number=1, player1_score=11, player2_score=8)
    score2_2 = MatchScore(match_id=match2.id, set_number=2, player1_score=11, player2_score=9)
    init_database.session.add_all([score2_1, score2_2])
    init_database.session.commit()

    # --- Match 3: P1 beats P3 (11-6, 11-4) ---
    match3 = Match(category_id=category.id, group_id=group.id, player1_id=p1.user_id, player2_id=p3.user_id, round=0, match_order=3, stage=MatchStage.GROUP, completed=True, winning_player_id=p1.user_id, losing_player_id=p3.user_id)
    init_database.session.add(match3)
    init_database.session.commit()
    score3_1 = MatchScore(match_id=match3.id, set_number=1, player1_score=11, player2_score=6)
    score3_2 = MatchScore(match_id=match3.id, set_number=2, player1_score=11, player2_score=4)
    init_database.session.add_all([score3_1, score3_2])
    init_database.session.commit()

    # Call the service method
    standings_list = BracketService.update_group_standings(group.id)

    # Assertions
    assert len(standings_list) == 3

    p1_s = next((s for s in standings_list if s.player_id == p1.user_id), None)
    p2_s = next((s for s in standings_list if s.player_id == p2.user_id), None)
    p3_s = next((s for s in standings_list if s.player_id == p3.user_id), None)

    assert p1_s is not None
    assert p2_s is not None
    assert p3_s is not None

    # Check P1 (Winner - 2 wins)
    assert p1_s.matches_played == 2
    assert p1_s.matches_won == 2
    assert p1_s.matches_lost == 0
    assert p1_s.sets_won == 4
    assert p1_s.sets_lost == 0
    assert p1_s.points_won == 44 # (11+11) + (11+11)
    assert p1_s.points_lost == 22 # (5+7) + (6+4)
    assert p1_s.position == 1

    # Check P2 (Middle - 1 win, 1 loss)
    assert p2_s.matches_played == 2
    assert p2_s.matches_won == 1
    assert p2_s.matches_lost == 1
    assert p2_s.sets_won == 2
    assert p2_s.sets_lost == 2
    assert p2_s.points_won == 34 # (5+7) + (11+11)
    assert p2_s.points_lost == 40 # (11+11) + (8+9)
    assert p2_s.position == 2

    # Check P3 (Loser - 2 losses)
    assert p3_s.matches_played == 2
    assert p3_s.matches_won == 0
    assert p3_s.matches_lost == 2
    assert p3_s.sets_won == 0
    assert p3_s.sets_lost == 4
    assert p3_s.points_won == 27 # (8+9) + (6+4)
    assert p3_s.points_lost == 44 # (11+11) + (11+11)
    assert p3_s.position == 3