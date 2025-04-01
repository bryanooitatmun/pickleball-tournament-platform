import pytest
from app import db
from app.models import (
    Tournament, TournamentCategory, Match, Group, GroupStanding, Team,
    Registration, User, PlayerProfile, TournamentFormat, MatchStage,
    MatchScore, CategoryType
)
from app.helpers.tournament import (
    _generate_group_stage, _generate_knockout_from_groups, _generate_single_elimination
)
from datetime import date, timedelta

# Import helper functions
from tests.test_bracket_service import (
    create_test_tournament, create_test_category, create_test_player,
    create_test_registration
)
from tests.test_bracket_service_extended import create_test_group

def test_position_codes_in_group_stage(init_database):
    """Test that position codes are correctly assigned in group stage matches"""
    # Setup
    tournament = create_test_tournament(init_database.session, format=TournamentFormat.GROUP_KNOCKOUT)
    category = create_test_category(init_database.session, tournament, category_type=CategoryType.MENS_SINGLES)
    
    # Create players
    players = [
        create_test_player(init_database.session, f"pc{i}") for i in range(1, 9)
    ]
    
    # Create registrations
    for player in players:
        create_test_registration(init_database.session, category, player)
    
    # Generate group stage
    category.group_count = 2  # 2 groups
    result = _generate_group_stage(category)
    assert result is True
    
    # Check that matches were created with position codes
    groups = Group.query.filter_by(category_id=category.id).all()
    assert len(groups) == 2
    
    # Get group matches
    for group in groups:
        matches = Match.query.filter_by(group_id=group.id).all()
        assert len(matches) > 0
        
        # Check that each match has position codes
        for match in matches:
            assert match.player1_code is not None
            assert match.player2_code is not None
            
            # Codes should follow the format "A1", "B2", etc.
            assert match.player1_code.startswith(group.name)
            assert match.player2_code.startswith(group.name)
            assert match.player1_code[1:].isdigit()
            assert match.player2_code[1:].isdigit()

def test_position_codes_in_knockout_stage(init_database):
    """Test that position codes are correctly assigned in knockout stage matches"""
    # Setup
    tournament = create_test_tournament(init_database.session, format=TournamentFormat.GROUP_KNOCKOUT)
    category = create_test_category(init_database.session, tournament, category_type=CategoryType.MENS_SINGLES)
    
    # Create players for 2 groups
    players = [
        create_test_player(init_database.session, f"kpc{i}") for i in range(1, 9)
    ]
    
    # Create registrations
    for player in players:
        create_test_registration(init_database.session, category, player)
    
    # Create groups and standings manually to control group positions
    group_a = create_test_group(init_database.session, category, "A")
    group_b = create_test_group(init_database.session, category, "B")
    
    # Add standings for group A
    for i, player in enumerate(players[:4]):
        standing = GroupStanding(
            group_id=group_a.id,
            player_id=player.user_id,
            position=i+1,
            matches_played=3,
            matches_won=3-i,
            matches_lost=i
        )
        init_database.session.add(standing)
    
    # Add standings for group B
    for i, player in enumerate(players[4:]):
        standing = GroupStanding(
            group_id=group_b.id,
            player_id=player.user_id,
            position=i+1,
            matches_played=3,
            matches_won=3-i,
            matches_lost=i
        )
        init_database.session.add(standing)
    
    init_database.session.commit()
    
    # Set teams advancing per group
    category.teams_advancing_per_group = 2
    
    # Generate knockout stage
    result = _generate_knockout_from_groups(category)
    assert result is True
    
    # Check that knockout matches were created with position codes
    knockout_matches = Match.query.filter_by(
        category_id=category.id,
        stage=MatchStage.KNOCKOUT
    ).all()
    
    assert len(knockout_matches) > 0
    
    # All matches should have position codes
    for match in knockout_matches:
        assert match.player1_code is not None, f"Match round {match.round}, order {match.match_order} missing player1_code"
        assert match.player2_code is not None, f"Match round {match.round}, order {match.match_order} missing player2_code"
    
    # Semifinal matches should have coded positions for quarterfinal winners
    semifinal_matches = [m for m in knockout_matches if m.round == 2]
    assert len(semifinal_matches) == 2
    
    for match in semifinal_matches:
        if match.match_order == 0:
            assert match.player1_code == "QF1", f"Expected QF1, got {match.player1_code}"
            assert match.player2_code == "QF2", f"Expected QF2, got {match.player2_code}"
        
        if match.match_order == 1:
            assert match.player1_code == "QF3", f"Expected QF3, got {match.player1_code}"
            assert match.player2_code == "QF4", f"Expected QF4, got {match.player2_code}"
    
    # Final match should be coded with semifinal winners
    final_matches = [m for m in knockout_matches if m.round == 1]
    assert len(final_matches) == 1
    assert final_matches[0].player1_code == "SF1"
    assert final_matches[0].player2_code == "SF2"

def test_knockout_generation_without_completed_group_stage(init_database):
    """Test that knockout bracket can be generated even if group stage isn't completed"""
    # Setup
    tournament = create_test_tournament(init_database.session, format=TournamentFormat.GROUP_KNOCKOUT)
    category = create_test_category(init_database.session, tournament, category_type=CategoryType.MENS_SINGLES)
    
    # Create players
    players = [
        create_test_player(init_database.session, f"kg{i}") for i in range(1, 9)
    ]
    
    # Create registrations
    for player in players:
        create_test_registration(init_database.session, category, player)
    
    # Create groups but NO standings
    group_a = create_test_group(init_database.session, category, "A")
    group_b = create_test_group(init_database.session, category, "B")
    
    init_database.session.commit()
    
    # Set teams advancing per group
    category.teams_advancing_per_group = 2
    
    # Generate knockout stage without completed group stage
    result = _generate_knockout_from_groups(category)
    assert result is True
    
    # Check that knockout matches were created with position codes
    knockout_matches = Match.query.filter_by(
        category_id=category.id,
        stage=MatchStage.KNOCKOUT
    ).all()
    
    assert len(knockout_matches) > 0
    
    # Verify all matches have position codes based on group names (A1, B2, etc.)
    first_round_matches = [m for m in knockout_matches if m.round == knockout_matches[0].round]
    for match in first_round_matches:
        assert match.player1_code is not None
        assert match.player2_code is not None
        # Check format of code (should be group letter + position number)
        assert match.player1_code[0] in ["A", "B"]
        assert match.player2_code[0] in ["A", "B"]
        assert match.player1_code[1:].isdigit()
        assert match.player2_code[1:].isdigit()

def test_position_codes_in_single_elimination(init_database):
    """Test that position codes are correctly assigned in single elimination tournament"""
    # Setup
    tournament = create_test_tournament(init_database.session, format=TournamentFormat.SINGLE_ELIMINATION)
    category = create_test_category(init_database.session, tournament, category_type=CategoryType.MENS_SINGLES)
    
    # Create players
    players = [
        create_test_player(init_database.session, f"se{i}") for i in range(1, 9)
    ]
    
    # Create registrations with seeds
    for i, player in enumerate(players):
        reg = create_test_registration(init_database.session, category, player)
        reg.seed = i + 1
    
    init_database.session.commit()
    
    # Generate single elimination bracket with seeding
    result = _generate_single_elimination(category, use_seeding=True)
    assert result is True
    
    # Check that matches were created with position codes
    matches = Match.query.filter_by(category_id=category.id).all()
    assert len(matches) > 0
    
    # First round matches should all have codes
    first_round_matches = [m for m in matches if m.round == 3]  # Assumed to be quarterfinals
    assert len(first_round_matches) > 0
    
    for match in first_round_matches:
        assert match.player1_code is not None
        assert match.player2_code is not None
    
    # Semifinal matches should have numeric codes
    semifinal_matches = [m for m in matches if m.round == 2]
    assert len(semifinal_matches) == 2
    
    # Final match should have SF1/SF2 codes
    final_matches = [m for m in matches if m.round == 1]
    assert len(final_matches) == 1
    assert final_matches[0].player1_code == "SF1"
    assert final_matches[0].player2_code == "SF2"
    
    # Check for 3rd place match if created
    third_place_matches = [m for m in matches if m.round == 1.5]
    if third_place_matches:
        assert len(third_place_matches) == 1
        assert third_place_matches[0].player1_code == "L-SF1"
        assert third_place_matches[0].player2_code == "L-SF2"