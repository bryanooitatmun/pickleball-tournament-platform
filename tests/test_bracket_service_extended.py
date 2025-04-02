import pytest
from app import db
from app.models import (
    Tournament, TournamentCategory, Match, Group, GroupStanding, Team,
    Registration, User, PlayerProfile, TournamentFormat, MatchStage,
    MatchScore, CategoryType, TournamentStatus
)
from app.services.bracket_service import BracketService
from datetime import date, timedelta

# Import helper functions from the existing test file
from tests.test_bracket_service import (
    create_test_tournament, create_test_category, create_test_player,
    create_test_registration
)

# Additional helper functions
def create_test_team(db_session, player1, player2, category):
    """Create a test doubles team"""
    team = Team(
        player1_id=player1.user_id,
        player2_id=player2.user_id,
        category_id=category.id
    )
    db_session.add(team)
    db_session.commit()
    return team

def create_test_group(db_session, category, name="Group A"):
    """Create a test group for group stages"""
    group = Group(category_id=category.id, name=name)
    db_session.add(group)
    db_session.commit()
    return group

def create_test_knockout_match(db_session, category, round_num, player1=None, player2=None, 
                              team1=None, team2=None, group=None, match_order=1, completed=False):
    """Create a test knockout match"""
    match = Match(
        category_id=category.id,
        round=round_num,
        match_order=match_order,
        stage=MatchStage.GROUP if group else MatchStage.KNOCKOUT,
        group_id=group.id if group else None,
        completed=completed
    )
    
    if player1 and player2:  # Singles match
        match.player1_id = player1.user_id
        match.player2_id = player2.user_id
    elif team1 and team2:  # Doubles match
        match.team1_id = team1.id
        match.team2_id = team2.id
    
    db_session.add(match)
    db_session.commit()
    return match

def add_test_scores(db_session, match, p1_scores, p2_scores):
    """Add test scores to a match"""
    for i, (p1_score, p2_score) in enumerate(zip(p1_scores, p2_scores), 1):
        score = MatchScore(
            match_id=match.id,
            set_number=i,
            player1_score=p1_score,
            player2_score=p2_score
        )
        db_session.add(score)
    db_session.commit()

# --- Extended Tests for BracketService ---

def test_get_bracket_data_singles_elimination(init_database):
    """Test get_bracket_data for a singles elimination tournament"""
    # Setup
    tournament = create_test_tournament(init_database.session, format=TournamentFormat.SINGLE_ELIMINATION)
    category = create_test_category(init_database.session, tournament, category_type=CategoryType.MENS_SINGLES)
    
    # Create 4 players for a simple bracket
    p1 = create_test_player(init_database.session, "bracket1")
    p2 = create_test_player(init_database.session, "bracket2")
    p3 = create_test_player(init_database.session, "bracket3")
    p4 = create_test_player(init_database.session, "bracket4")
    
    # Create semifinal matches
    semi1 = create_test_knockout_match(init_database.session, category, round_num=2, 
                                      player1=p1, player2=p2, match_order=1)
    semi2 = create_test_knockout_match(init_database.session, category, round_num=2, 
                                      player1=p3, player2=p4, match_order=2)
    
    # Create final match
    final = create_test_knockout_match(init_database.session, category, round_num=1, 
                                      player1=None, player2=None, match_order=1)
    
    # Test
    bracket_data = BracketService.get_bracket_data(category.id)
    
    # Assert
    assert bracket_data['category'] == category
    assert bracket_data['format'] == tournament.format
    assert bracket_data['group_stage'] is False
    assert len(bracket_data['groups']) == 0  # No groups in single elimination
    
    # Check knockout rounds
    assert 1 in bracket_data['knockout_rounds']  # Finals (round 1)
    assert 2 in bracket_data['knockout_rounds']  # Semifinals (round 2)
    assert len(bracket_data['knockout_rounds'][1]) == 1  # 1 match in finals
    assert len(bracket_data['knockout_rounds'][2]) == 2  # 2 matches in semifinals
    
    # Check match ordering within rounds
    round2_matches = bracket_data['knockout_rounds'][2]
    assert round2_matches[0].match_order < round2_matches[1].match_order

def test_get_bracket_data_with_group_stage(init_database):
    """Test get_bracket_data for a tournament with group stage + knockout"""
    # Setup
    tournament = create_test_tournament(init_database.session, format=TournamentFormat.GROUP_KNOCKOUT)
    category = create_test_category(init_database.session, tournament, category_type=CategoryType.MENS_SINGLES)
    
    # Create 6 players (2 groups of 3)
    players = [create_test_player(init_database.session, f"group{i}") for i in range(1, 7)]
    
    # Create 2 groups
    group_a = create_test_group(init_database.session, category, "Group A")
    group_b = create_test_group(init_database.session, category, "Group B")
    
    # Add players to group standings
    for i, p in enumerate(players[:3]):
        standing = GroupStanding(group_id=group_a.id, player_id=p.user_id, position=i+1)
        init_database.session.add(standing)
        
    for i, p in enumerate(players[3:]):
        standing = GroupStanding(group_id=group_b.id, player_id=p.user_id, position=i+1)
        init_database.session.add(standing)
    
    init_database.session.commit()
    
    # Create group matches
    # Group A
    match_a1 = create_test_knockout_match(init_database.session, category, round_num=0, 
                                         player1=players[0], player2=players[1], 
                                         group=group_a, match_order=1, completed=True)
    match_a1.stage = MatchStage.GROUP
    match_a1.winning_player_id = players[0].user_id
    match_a1.losing_player_id = players[1].user_id
    init_database.session.commit()
    
    add_test_scores(init_database.session, match_a1, [11, 11], [9, 7])
    
    match_a2 = create_test_knockout_match(init_database.session, category, round_num=0, 
                                         player1=players[1], player2=players[2], 
                                         group=group_a, match_order=2, completed=True)
    match_a2.stage = MatchStage.GROUP
    match_a2.winning_player_id = players[1].user_id
    match_a2.losing_player_id = players[2].user_id
    init_database.session.commit()
    
    add_test_scores(init_database.session, match_a2, [11, 11], [9, 8])
    
    match_a3 = create_test_knockout_match(init_database.session, category, round_num=0, 
                                         player1=players[0], player2=players[2], 
                                         group=group_a, match_order=3, completed=True)
    match_a3.stage = MatchStage.GROUP
    match_a3.winning_player_id = players[0].user_id
    match_a3.losing_player_id = players[2].user_id
    init_database.session.commit()
    
    add_test_scores(init_database.session, match_a3, [11, 11], [5, 6])
    
    # Group B (same pattern)
    match_b1 = create_test_knockout_match(init_database.session, category, round_num=0, 
                                         player1=players[3], player2=players[4], 
                                         group=group_b, match_order=1, completed=True)
    match_b1.stage = MatchStage.GROUP
    match_b1.winning_player_id = players[3].user_id
    match_b1.losing_player_id = players[4].user_id
    init_database.session.commit()
    
    add_test_scores(init_database.session, match_b1, [11, 11], [8, 7])
    
    # Create knockout matches (semifinal)
    semi1 = create_test_knockout_match(init_database.session, category, round_num=2, 
                                     player1=players[0], player2=players[4], 
                                     match_order=1)
    semi1.stage = MatchStage.KNOCKOUT
    init_database.session.commit()
    
    semi2 = create_test_knockout_match(init_database.session, category, round_num=2, 
                                     player1=players[3], player2=players[1], 
                                     match_order=2)
    semi2.stage = MatchStage.KNOCKOUT
    init_database.session.commit()
    
    # Create knockout match (final)
    final = create_test_knockout_match(init_database.session, category, round_num=1, 
                                     player1=None, player2=None, match_order=1)
    final.stage = MatchStage.KNOCKOUT
    init_database.session.commit()
    
    # Test
    bracket_data = BracketService.get_bracket_data(category.id)
    
    # Assert
    assert bracket_data['category'] == category
    assert bracket_data['format'] == tournament.format
    assert bracket_data['group_stage'] is True
    
    # Check groups
    assert len(bracket_data['groups']) == 2  # 2 groups
    
    # Group A
    group_a_data = next((g for g in bracket_data['groups'] if g['group'].id == group_a.id), None)
    assert group_a_data is not None
    assert len(group_a_data['standings']) == 3  # 3 players
    assert len(group_a_data['matches']) == 3  # 3 matches
    
    # Group B
    group_b_data = next((g for g in bracket_data['groups'] if g['group'].id == group_b.id), None)
    assert group_b_data is not None
    assert len(group_b_data['standings']) > 0
    assert len(group_b_data['matches']) > 0
    
    # Check knockout rounds
    assert 1 in bracket_data['knockout_rounds']  # Finals
    assert 2 in bracket_data['knockout_rounds']  # Semifinals
    assert len(bracket_data['knockout_rounds'][1]) == 1  # 1 match in finals
    assert len(bracket_data['knockout_rounds'][2]) == 2  # 2 matches in semifinals

def test_get_group_data(init_database):
    """Test get_group_data for fetching group stage information"""
    # Setup
    tournament = create_test_tournament(init_database.session, format=TournamentFormat.GROUP_KNOCKOUT)
    category = create_test_category(init_database.session, tournament, category_type=CategoryType.MENS_SINGLES)
    
    # Create 3 players for a group
    p1 = create_test_player(init_database.session, "gd1")
    p2 = create_test_player(init_database.session, "gd2")
    p3 = create_test_player(init_database.session, "gd3")
    
    # Create group
    group = create_test_group(init_database.session, category, "Test Group")
    
    # Add players to group standings with different positions
    s1 = GroupStanding(group_id=group.id, player_id=p1.user_id, position=1, 
                    matches_played=2, matches_won=2, matches_lost=0,
                    sets_won=4, sets_lost=0, points_won=44, points_lost=20)
    s2 = GroupStanding(group_id=group.id, player_id=p2.user_id, position=2,
                    matches_played=2, matches_won=1, matches_lost=1,
                    sets_won=2, sets_lost=2, points_won=36, points_lost=34)
    s3 = GroupStanding(group_id=group.id, player_id=p3.user_id, position=3,
                    matches_played=2, matches_won=0, matches_lost=2,
                    sets_won=0, sets_lost=4, points_won=20, points_lost=46)
    init_database.session.add_all([s1, s2, s3])
    init_database.session.commit()
    
    # Create group matches
    match1 = create_test_knockout_match(init_database.session, category, round_num=0, 
                                      player1=p1, player2=p2, group=group, match_order=1, 
                                      completed=True)
    match1.stage = MatchStage.GROUP
    match1.winning_player_id = p1.user_id
    match1.losing_player_id = p2.user_id
    init_database.session.commit()
    
    add_test_scores(init_database.session, match1, [11, 11], [9, 7])
    
    match2 = create_test_knockout_match(init_database.session, category, round_num=0, 
                                      player1=p2, player2=p3, group=group, match_order=2, 
                                      completed=True)
    match2.stage = MatchStage.GROUP
    match2.winning_player_id = p2.user_id
    match2.losing_player_id = p3.user_id
    init_database.session.commit()
    
    add_test_scores(init_database.session, match2, [11, 11], [6, 5])
    
    match3 = create_test_knockout_match(init_database.session, category, round_num=0, 
                                      player1=p1, player2=p3, group=group, match_order=3, 
                                      completed=False)  # Not completed yet
    match3.stage = MatchStage.GROUP
    init_database.session.commit()
    
    # Test
    group_data = BracketService.get_group_data(category.id)
    
    # Assert
    assert len(group_data) == 1  # 1 group
    
    group_info = group_data[0]
    assert group_info['group'].id == group.id
    assert group_info['group'].name == "Test Group"
    
    # Check standings
    assert len(group_info['standings']) == 3  # 3 players
    assert group_info['standings'][0].position == 1  # First place
    assert group_info['standings'][0].player_id == p1.user_id
    assert group_info['standings'][1].position == 2  # Second place
    assert group_info['standings'][1].player_id == p2.user_id
    assert group_info['standings'][2].position == 3  # Third place
    assert group_info['standings'][2].player_id == p3.user_id
    
    # Check matches
    assert len(group_info['matches']) == 3  # 3 matches
    
    # Verify they're ordered correctly
    assert group_info['matches'][0].match_order < group_info['matches'][1].match_order
    assert group_info['matches'][1].match_order < group_info['matches'][2].match_order

def test_update_standing_from_match(init_database):
    """Test _update_standing_from_match (internal method) with singles match"""
    # Setup
    tournament = create_test_tournament(init_database.session, format=TournamentFormat.GROUP_KNOCKOUT)
    category = create_test_category(init_database.session, tournament, category_type=CategoryType.MENS_SINGLES)
    
    # Create players
    p1 = create_test_player(init_database.session, "usm1")
    p2 = create_test_player(init_database.session, "usm2")
    
    # Create group
    group = create_test_group(init_database.session, category)
    
    # Create standings for both players
    s1 = GroupStanding(group_id=group.id, player_id=p1.user_id)
    s2 = GroupStanding(group_id=group.id, player_id=p2.user_id)
    init_database.session.add_all([s1, s2])
    init_database.session.commit()
    
    # Create a match with player1 winning
    match = create_test_knockout_match(init_database.session, category, round_num=0, 
                                     player1=p1, player2=p2, group=group, completed=True)
    match.stage = MatchStage.GROUP
    match.winning_player_id = p1.user_id
    match.losing_player_id = p2.user_id
    init_database.session.commit()
    
    # Add scores: p1 wins both sets
    score1 = MatchScore(match_id=match.id, set_number=1, player1_score=11, player2_score=5)
    score2 = MatchScore(match_id=match.id, set_number=2, player1_score=11, player2_score=7)
    init_database.session.add_all([score1, score2])
    init_database.session.commit()
    
    # Initial standings should be zeros
    assert s1.matches_played == 0
    assert s1.matches_won == 0
    assert s1.sets_won == 0
    assert s1.points_won == 0
    
    # Test for player 1 (winner)
    BracketService._update_standing_from_match(s1, match, is_team1=True)
    
    # Assert player 1 stats updated correctly
    assert s1.matches_played == 1
    assert s1.matches_won == 1
    assert s1.matches_lost == 0
    assert s1.sets_won == 2  # Won both sets
    assert s1.sets_lost == 0
    assert s1.points_won == 22  # 11 + 11
    assert s1.points_lost == 12  # 5 + 7
    
    # Test for player 2 (loser)
    BracketService._update_standing_from_match(s2, match, is_team1=False)
    
    # Assert player 2 stats updated correctly
    assert s2.matches_played == 1
    assert s2.matches_won == 0
    assert s2.matches_lost == 1
    assert s2.sets_won == 0
    assert s2.sets_lost == 2
    assert s2.points_won == 12  # 5 + 7
    assert s2.points_lost == 22  # 11 + 11

def test_update_standing_from_match_doubles(init_database):
    """Test _update_standing_from_match (internal method) with doubles match"""
    # Setup
    tournament = create_test_tournament(init_database.session, format=TournamentFormat.GROUP_KNOCKOUT)
    category = create_test_category(init_database.session, tournament, category_type=CategoryType.MENS_DOUBLES)
    
    # Create players for 2 teams
    p1 = create_test_player(init_database.session, "dbl1")
    p2 = create_test_player(init_database.session, "dbl2")
    p3 = create_test_player(init_database.session, "dbl3")
    p4 = create_test_player(init_database.session, "dbl4")
    
    # Create teams
    team1 = create_test_team(init_database.session, p1, p2, category)
    team2 = create_test_team(init_database.session, p3, p4, category)
    
    # Create group
    group = create_test_group(init_database.session, category)
    
    # Create standings for both teams
    s1 = GroupStanding(group_id=group.id, team_id=team1.id)
    s2 = GroupStanding(group_id=group.id, team_id=team2.id)
    init_database.session.add_all([s1, s2])
    init_database.session.commit()
    
    # Create a match with team1 winning
    match = create_test_knockout_match(init_database.session, category, round_num=0, 
                                     team1=team1, team2=team2, group=group, completed=True)
    match.stage = MatchStage.GROUP
    match.winning_team_id = team1.id
    match.losing_team_id = team2.id
    init_database.session.commit()
    
    # Add scores: team1 wins both sets
    score1 = MatchScore(match_id=match.id, set_number=1, player1_score=11, player2_score=9)
    score2 = MatchScore(match_id=match.id, set_number=2, player1_score=11, player2_score=8)
    init_database.session.add_all([score1, score2])
    init_database.session.commit()
    
    # Test for team 1 (winner)
    BracketService._update_standing_from_match(s1, match, is_team1=True)
    
    # Assert team 1 stats updated correctly
    assert s1.matches_played == 1
    assert s1.matches_won == 1
    assert s1.matches_lost == 0
    assert s1.sets_won == 2  # Won both sets
    assert s1.sets_lost == 0
    assert s1.points_won == 22  # 11 + 11
    assert s1.points_lost == 17  # 9 + 8
    
    # Test for team 2 (loser)
    BracketService._update_standing_from_match(s2, match, is_team1=False)
    
    # Assert team 2 stats updated correctly
    assert s2.matches_played == 1
    assert s2.matches_won == 0
    assert s2.matches_lost == 1
    assert s2.sets_won == 0
    assert s2.sets_lost == 2
    assert s2.points_won == 17  # 9 + 8
    assert s2.points_lost == 22  # 11 + 11

def test_calculate_group_positions(init_database):
    """Test _calculate_group_positions method for correct sorting"""
    # Setup - using direct setup for simplicity
    # Create standings with controlled values to test sorting
    
    tournament = create_test_tournament(init_database.session)
    category = create_test_category(init_database.session, tournament)
    group = create_test_group(init_database.session, category)
    
    # Create players
    players = [
        create_test_player(init_database.session, "pos1"),
        create_test_player(init_database.session, "pos2"),
        create_test_player(init_database.session, "pos3"),
        create_test_player(init_database.session, "pos4")
    ]
    
    # Create standings with different stats for sorting
    standings = [
        # matches_won, sets_won, sets_lost, points_won, points_lost
        GroupStanding(group_id=group.id, player_id=players[0].user_id, matches_won=2, 
                   sets_won=4, sets_lost=0, points_won=44, points_lost=20),  # 1st place
        GroupStanding(group_id=group.id, player_id=players[1].user_id, matches_won=2, 
                   sets_won=4, sets_lost=2, points_won=50, points_lost=40),  # 2nd place (same wins/sets as #3 but worse point diff)
        GroupStanding(group_id=group.id, player_id=players[2].user_id, matches_won=2, 
                   sets_won=4, sets_lost=2, points_won=52, points_lost=38),  # 1st place (same wins/sets as #2 but better point diff)
        GroupStanding(group_id=group.id, player_id=players[3].user_id, matches_won=0, 
                   sets_won=0, sets_lost=4, points_won=20, points_lost=46)   # 4th place
    ]
    init_database.session.add_all(standings)
    init_database.session.commit()
    
    # Test
    BracketService._calculate_group_positions(standings)
    
    # Sort standings by assigned position
    sorted_standings = sorted(standings, key=lambda s: s.position)
    
    # Assert
    assert len(sorted_standings) == 4
    
    # Players with most matches won should be first, then sets differential, then points differential
    assert sorted_standings[0].player_id == players[0].user_id  # Best record
    assert sorted_standings[0].position == 1
    
    assert sorted_standings[1].player_id == players[2].user_id  # Better point differential
    assert sorted_standings[1].position == 2
    
    assert sorted_standings[2].player_id == players[1].user_id  # Worse point differential
    assert sorted_standings[2].position == 3
    
    assert sorted_standings[3].player_id == players[3].user_id  # Worst record
    assert sorted_standings[3].position == 4

def test_process_match_for_standings_singles(init_database):
    """Test _process_match_for_standings with a singles match"""
    # Setup
    tournament = create_test_tournament(init_database.session, format=TournamentFormat.GROUP_KNOCKOUT)
    category = create_test_category(init_database.session, tournament, category_type=CategoryType.MENS_SINGLES)
    
    # Create players
    p1 = create_test_player(init_database.session, "proc1")
    p2 = create_test_player(init_database.session, "proc2")
    
    # Create group
    group = create_test_group(init_database.session, category)
    
    # Create a match
    match = create_test_knockout_match(init_database.session, category, round_num=0, 
                                     player1=p1, player2=p2, group=group, completed=True)
    match.stage = MatchStage.GROUP
    match.winning_player_id = p1.user_id
    match.losing_player_id = p2.user_id
    init_database.session.commit()
    
    # Add scores
    score1 = MatchScore(match_id=match.id, set_number=1, player1_score=11, player2_score=5)
    score2 = MatchScore(match_id=match.id, set_number=2, player1_score=11, player2_score=7)
    init_database.session.add_all([score1, score2])
    init_database.session.commit()
    
    # Test
    # Pre-create GroupStanding objects with initialized fields
    p1_standing = GroupStanding(
        group_id=group.id, 
        player_id=p1.user_id,
        matches_played=0,
        matches_won=0,
        matches_lost=0,
        sets_won=0,
        sets_lost=0,
        points_won=0,
        points_lost=0
    )
    
    p2_standing = GroupStanding(
        group_id=group.id, 
        player_id=p2.user_id,
        matches_played=0,
        matches_won=0,
        matches_lost=0,
        sets_won=0,
        sets_lost=0,
        points_won=0,
        points_lost=0
    )
    
    init_database.session.add_all([p1_standing, p2_standing])
    init_database.session.commit()
    
    # Set up the standings dictionary with our pre-initialized standings
    standings = {
        p1.user_id: p1_standing,
        p2.user_id: p2_standing
    }

    BracketService._process_match_for_standings(match, standings, is_doubles=False)
    

    # Assert
    assert len(standings) == 2  # Both players should have standings
    assert p1.user_id in standings
    assert p2.user_id in standings
    
    # Check player 1 standings
    p1_standing = standings[p1.user_id]
    assert p1_standing.group_id == group.id
    assert p1_standing.player_id == p1.user_id
    assert p1_standing.matches_played == 1
    assert p1_standing.matches_won == 1
    assert p1_standing.matches_lost == 0
    
    # Check player 2 standings
    p2_standing = standings[p2.user_id]
    assert p2_standing.group_id == group.id
    assert p2_standing.player_id == p2.user_id
    assert p2_standing.matches_played == 1
    assert p2_standing.matches_won == 0
    assert p2_standing.matches_lost == 1

def test_process_match_for_standings_doubles(init_database):
    """Test _process_match_for_standings with a doubles match"""
    # Setup
    tournament = create_test_tournament(init_database.session, format=TournamentFormat.GROUP_KNOCKOUT)
    category = create_test_category(init_database.session, tournament, category_type=CategoryType.MENS_DOUBLES)
    
    # Create players
    p1 = create_test_player(init_database.session, "procd1")
    p2 = create_test_player(init_database.session, "procd2")
    p3 = create_test_player(init_database.session, "procd3")
    p4 = create_test_player(init_database.session, "procd4")
    
    # Create teams
    team1 = create_test_team(init_database.session, p1, p2, category)
    team2 = create_test_team(init_database.session, p3, p4, category)
    
    # Create group
    group = create_test_group(init_database.session, category)
    
    # Create a match
    match = create_test_knockout_match(init_database.session, category, round_num=0, 
                                     team1=team1, team2=team2, group=group, completed=True)
    match.stage = MatchStage.GROUP
    match.winning_team_id = team1.id
    match.losing_team_id = team2.id
    init_database.session.commit()
    
    # Add scores
    score1 = MatchScore(match_id=match.id, set_number=1, player1_score=11, player2_score=9)
    score2 = MatchScore(match_id=match.id, set_number=2, player1_score=11, player2_score=6)
    init_database.session.add_all([score1, score2])
    init_database.session.commit()
    
    # Test
    # Pre-create GroupStanding objects with initialized fields
    team1_standing = GroupStanding(
        group_id=group.id, 
        team_id=team1.id,
        matches_played=0,
        matches_won=0,
        matches_lost=0,
        sets_won=0,
        sets_lost=0,
        points_won=0,
        points_lost=0
    )
    
    team2_standing = GroupStanding(
        group_id=group.id, 
        team_id=team2.id,
        matches_played=0,
        matches_won=0,
        matches_lost=0,
        sets_won=0,
        sets_lost=0,
        points_won=0,
        points_lost=0
    )
    
    init_database.session.add_all([team1_standing, team2_standing])
    init_database.session.commit()
    
    # Set up the standings dictionary with our pre-initialized standings
    standings = {
        team1.id: team1_standing,
        team2.id: team2_standing
    }
    BracketService._process_match_for_standings(match, standings, is_doubles=True)
    
    # Assert
    assert len(standings) == 2  # Both teams should have standings
    assert team1.id in standings
    assert team2.id in standings
    
    # Check team 1 standings
    t1_standing = standings[team1.id]
    assert t1_standing.group_id == group.id
    assert t1_standing.team_id == team1.id
    assert t1_standing.matches_played == 1
    assert t1_standing.matches_won == 1
    assert t1_standing.matches_lost == 0
    
    # Check team 2 standings
    t2_standing = standings[team2.id]
    assert t2_standing.group_id == group.id
    assert t2_standing.team_id == team2.id
    assert t2_standing.matches_played == 1
    assert t2_standing.matches_won == 0
    assert t2_standing.matches_lost == 1

def test_update_database_standings_removal(init_database):
    """Test _update_database_standings removes old standings not in current list"""
    # Setup
    tournament = create_test_tournament(init_database.session)
    category = create_test_category(init_database.session, tournament)
    group = create_test_group(init_database.session, category)
    
    # Create 4 players
    players = [
        create_test_player(init_database.session, f"updbs{i}") for i in range(1, 5)
    ]
    
    # Create standings for all 4 players
    for p in players:
        s = GroupStanding(group_id=group.id, player_id=p.user_id)
        init_database.session.add(s)
    init_database.session.commit()
    
    # Verify initial state
    initial_standings = GroupStanding.query.filter_by(group_id=group.id).all()
    assert len(initial_standings) == 4
    
    # Setup current standings dictionary with only 2 players
    current_standings = {}
    for i, p in enumerate(players[:2]):
        s = GroupStanding.query.filter_by(group_id=group.id, player_id=p.user_id).first()
        current_standings[p.user_id] = s
    
    # Test
    BracketService._update_database_standings(current_standings, group.id)
    
    # Assert
    remaining_standings = GroupStanding.query.filter_by(group_id=group.id).all()
    assert len(remaining_standings) == 2  # Should have removed 2 standings
    
    # Check that only the correct standings remain
    remaining_ids = [s.player_id for s in remaining_standings]
    assert players[0].user_id in remaining_ids
    assert players[1].user_id in remaining_ids
    assert players[2].user_id not in remaining_ids
    assert players[3].user_id not in remaining_ids
