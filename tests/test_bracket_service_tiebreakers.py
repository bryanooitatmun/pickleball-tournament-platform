import unittest
from unittest.mock import patch, MagicMock
from app.services.bracket_service import BracketService
from app.models import GroupStanding, Match, MatchScore

class TestBracketServiceTiebreakers(unittest.TestCase):
    """Test cases for the tiebreak implementation in BracketService"""

    def test_calculate_group_positions_with_tiebreakers(self):
        """Test that the head-to-head tiebreaker is applied correctly"""
        # Create mock standings
        mock_standings = [
            MagicMock(
                group_id=1,
                player_id=1,
                team_id=None,
                matches_won=3,
                matches_lost=1,
                sets_won=6,
                sets_lost=2,
                points_won=60,
                points_lost=40
            ),
            MagicMock(
                group_id=1,
                player_id=2,
                team_id=None,
                matches_won=3,
                matches_lost=1,
                sets_won=6,
                sets_lost=3,
                points_won=58,
                points_lost=45
            ),
            MagicMock(
                group_id=1,
                player_id=3,
                team_id=None,
                matches_won=1,
                matches_lost=3,
                sets_won=3,
                sets_lost=6,
                points_won=45,
                points_lost=58
            ),
            MagicMock(
                group_id=1,
                player_id=4,
                team_id=None,
                matches_won=1,
                matches_lost=3,
                sets_won=2,
                sets_lost=6,
                points_won=40,
                points_lost=60
            ),
        ]

        # Mock the head-to-head match between the first two players
        # Player 2 beat Player 1 head-to-head
        mock_match = MagicMock(
            group_id=1,
            player1_id=1,
            player2_id=2,
            team1_id=None,
            team2_id=None,
            winning_player_id=2,
            completed=True
        )

        with patch('app.services.bracket_service.Match.query') as mock_query:
            # Set up the mock query for _apply_tiebreakers
            mock_filter_by = MagicMock()
            mock_filter = MagicMock()
            mock_filter.all.return_value = [mock_match]
            mock_filter_by.filter.return_value = mock_filter
            mock_query.filter_by.return_value = mock_filter_by

            # Call the method under test
            BracketService._calculate_group_positions(mock_standings)

            # Check that positions were assigned correctly
            # Player 2 should be first because they won head-to-head against Player 1
            self.assertEqual(mock_standings[0].position, 2)  # Player 1 
            self.assertEqual(mock_standings[1].position, 1)  # Player 2
            # Player 3 and 4 have the same win count, but player 3 has better point differential
            self.assertEqual(mock_standings[2].position, 3)  # Player 3
            self.assertEqual(mock_standings[3].position, 4)  # Player 4

    def test_apply_tiebreakers_with_head_to_head(self):
        """Test that _apply_tiebreakers correctly uses head-to-head record"""
        # Create mock tied standings with the same matches won
        tied_standings = [
            MagicMock(
                id=1,
                group_id=1,
                player_id=1,
                team_id=None,
                matches_won=2,
                matches_lost=1,
                points_won=30,
                points_lost=25
            ),
            MagicMock(
                id=2,
                group_id=1,
                player_id=2,
                team_id=None,
                matches_won=2,
                matches_lost=1,
                points_won=25,
                points_lost=20
            ),
        ]

        # Mock the head-to-head match: player 2 beat player 1
        mock_match = MagicMock(
            group_id=1,
            player1_id=1,
            player2_id=2,
            team1_id=None,
            team2_id=None,
            winning_player_id=2,
            completed=True
        )

        with patch('app.services.bracket_service.Match.query') as mock_query:
            # Set up the mock query
            mock_filter_by = MagicMock()
            mock_filter = MagicMock()
            mock_filter.all.return_value = [mock_match]
            mock_filter_by.filter.return_value = mock_filter
            mock_query.filter_by.return_value = mock_filter_by

            # Call the method under test
            result = BracketService._apply_tiebreakers(tied_standings)

            # Player 2 should be first because they won the head-to-head match
            self.assertEqual(result[0].id, 2)
            self.assertEqual(result[1].id, 1)

    def test_apply_tiebreakers_fallback_to_point_differential(self):
        """Test that when head-to-head is tied, it falls back to point differential"""
        # Create mock tied standings with the same matches won
        tied_standings = [
            MagicMock(
                id=1,
                group_id=1,
                player_id=1,
                team_id=None,
                matches_won=2,
                matches_lost=1,
                points_won=35,  # Better point differential (35-25 = 10)
                points_lost=25
            ),
            MagicMock(
                id=2,
                group_id=1,
                player_id=2,
                team_id=None,
                matches_won=2,
                matches_lost=1,
                points_won=30,  # Worse point differential (30-25 = 5)
                points_lost=25
            ),
        ]

        # No head-to-head matches between them
        with patch('app.services.bracket_service.Match.query') as mock_query:
            # Set up the mock query to return no matches
            mock_filter_by = MagicMock()
            mock_filter = MagicMock()
            mock_filter.all.return_value = []
            mock_filter_by.filter.return_value = mock_filter
            mock_query.filter_by.return_value = mock_filter_by

            # Call the method under test
            result = BracketService._apply_tiebreakers(tied_standings)

            # Player 1 should be first because they have better point differential
            self.assertEqual(result[0].id, 1)
            self.assertEqual(result[1].id, 2)

    def test_complex_tiebreaker_with_multiple_participants(self):
        """Test a more complex scenario with multiple tied participants"""
        # Create mock tied standings with the same matches won
        tied_standings = [
            MagicMock(
                id=1,
                group_id=1,
                player_id=1,
                team_id=None,
                matches_won=2,
                matches_lost=1,
                points_won=30,
                points_lost=25
            ),
            MagicMock(
                id=2,
                group_id=1,
                player_id=2,
                team_id=None,
                matches_won=2,
                matches_lost=1,
                points_won=28,
                points_lost=22
            ),
            MagicMock(
                id=3,
                group_id=1,
                player_id=3,
                team_id=None,
                matches_won=2,
                matches_lost=1,
                points_won=25,
                points_lost=20
            ),
        ]

        # Mock the head-to-head matches:
        # Player 1 beat Player 2
        # Player 2 beat Player 3
        # Player 3 beat Player 1
        # This creates a circular tie
        mock_matches = [
            MagicMock(
                group_id=1,
                player1_id=1,
                player2_id=2,
                winning_player_id=1,
                completed=True
            ),
            MagicMock(
                group_id=1,
                player1_id=2,
                player2_id=3,
                winning_player_id=2,
                completed=True
            ),
            MagicMock(
                group_id=1,
                player1_id=3,
                player2_id=1,
                winning_player_id=3,
                completed=True
            ),
        ]

        with patch('app.services.bracket_service.Match.query') as mock_query:
            # Set up the mock query
            mock_filter_by = MagicMock()
            mock_filter = MagicMock()
            mock_filter.all.return_value = mock_matches
            mock_filter_by.filter.return_value = mock_filter
            mock_query.filter_by.return_value = mock_filter_by

            # Call the method under test
            result = BracketService._apply_tiebreakers(tied_standings)

            # In a circular tie (1 beat 2, 2 beat 3, 3 beat 1), 
            # they all have 1 head-to-head win, so we fall back to point differential
            # Player 1: 30-25 = 5
            # Player 2: 28-22 = 6
            # Player 3: 25-20 = 5
            # Player 2 should be first, then Player 1 and Player 3 (or Player 3 then Player 1 depending on implementation)
            self.assertEqual(result[0].id, 2)  # Player 2 has best point differential
            # The other two have the same differential, so order depends on implementation


if __name__ == '__main__':
    unittest.main()
