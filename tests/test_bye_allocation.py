import unittest
from unittest.mock import patch, MagicMock, call
import random
from app.helpers.tournament import _distribute_byes_in_bracket, _apply_standard_seeding

class TestByeAllocation(unittest.TestCase):
    """Test the bye allocation logic for tournament brackets"""

    def test_apply_standard_seeding_size4(self):
        """Test standard seeding pattern for 4-slot bracket"""
        positions = list(range(4))  # [0, 1, 2, 3]
        seeded = _apply_standard_seeding(positions, 4)
        
        # Expected seeding pattern for 4-slot bracket:
        # Seed 1 at position 0, Seed 2 at position 3, Seed 3 at position 1, Seed 4 at position 2
        self.assertEqual(seeded, [0, 2, 1, 3])

    def test_apply_standard_seeding_size8(self):
        """Test standard seeding pattern for 8-slot bracket"""
        positions = list(range(8))  # [0, 1, 2, ..., 7]
        seeded = _apply_standard_seeding(positions, 8)
        
        # Expected seeding pattern for 8-slot bracket
        expected = [0, 4, 2, 6, 1, 5, 3, 7]
        self.assertEqual(seeded, expected)

    def test_distribute_byes_simple(self):
        """Test distributing participants with byes in a simple case"""
        # Create a list of 6 seeded participants (for an 8-slot bracket)
        participants = [
            {'seed': 1, 'name': 'Player 1'},
            {'seed': 2, 'name': 'Player 2'},
            {'seed': 3, 'name': 'Player 3'},
            {'seed': 4, 'name': 'Player 4'},
            {'seed': 5, 'name': 'Player 5'},
            {'seed': 6, 'name': 'Player 6'}
        ]
        
        # Distribute in an 8-slot bracket
        distributed = _distribute_byes_in_bracket(participants, 8)
        
        # Check the length and None positions
        self.assertEqual(len(distributed), 8)
        
        # In an 8-player bracket with 6 participants, seeds 1 and 2 should get byes
        # So positions that would face seeds 1 and 2 in the first round should be None
        # Typically positions 7 and 6
        seed_positions = _apply_standard_seeding(list(range(8)), 8)
        seed1_position = seed_positions[0]  # Position for seed 1
        seed2_position = seed_positions[1]  # Position for seed 2
        
        # Find the potential first-round opponents of seed 1 and seed 2
        # For seed 1, it's position 7
        # For seed 2, it's position 6
        opponent1_position = 7 if seed1_position == 0 else (seed1_position ^ 7)
        opponent2_position = 6 if seed2_position == 1 else (seed2_position ^ 7)
        
        # Check that byes are assigned to the correct positions
        self.assertEqual(distributed[opponent1_position], None)
        self.assertEqual(distributed[opponent2_position], None)
        
        # Check that players are assigned correctly (first to sixth seed)
        seed_1_pos = seed_positions[0]
        self.assertEqual(distributed[seed_1_pos]['name'], 'Player 1')

    def test_distribute_byes_with_many_byes(self):
        """Test distributing participants with many byes (large bracket)"""
        # Create a list of 10 seeded participants (for a 16-slot bracket)
        participants = [{'seed': i, 'name': f'Player {i}'} for i in range(1, 11)]
        
        # Distribute in a 16-slot bracket
        distributed = _distribute_byes_in_bracket(participants, 16)
        
        # Check the length
        self.assertEqual(len(distributed), 16)
        
        # Count None values (should be 6 byes)
        none_count = sum(1 for p in distributed if p is None)
        self.assertEqual(none_count, 6)
        
        # Check that the top 6 seeds get byes (their first round opponents are None)
        seed_positions = _apply_standard_seeding(list(range(16)), 16)
        
        # Find opponents for top 6 seeds
        # For a 16-bracket, seed 1 faces position 15, seed 2 faces 14, etc.
        opponent_positions = []
        for i in range(6):
            seed_pos = seed_positions[i]
            # XOR with 15 gives the opponent position in a 16-bracket
            opponent_pos = seed_pos ^ 15
            opponent_positions.append(opponent_pos)
            
        # Check all opponent positions have byes (None)
        for pos in opponent_positions:
            self.assertIsNone(distributed[pos], f"Expected bye at position {pos}")

    def test_different_bracket_sizes(self):
        """Test the bye allocation with different bracket sizes"""
        for bracket_size in [4, 8, 16, 32]:
            # Create test cases with varying numbers of participants
            participant_counts = [
                bracket_size - 1,  # Just one bye
                bracket_size // 2,  # Half byes
                2  # Minimal number of participants
            ]
            
            for count in participant_counts:
                # Create participants
                participants = [{'seed': i, 'name': f'Player {i}'} for i in range(1, count + 1)]
                
                # Distribute byes
                distributed = _distribute_byes_in_bracket(participants, bracket_size)
                
                # Verify correct size
                self.assertEqual(len(distributed), bracket_size)
                
                # Verify correct number of byes
                none_count = sum(1 for p in distributed if p is None)
                self.assertEqual(none_count, bracket_size - count)
                
                # Verify all participants are included
                participant_count = sum(1 for p in distributed if p is not None)
                self.assertEqual(participant_count, count)

if __name__ == '__main__':
    unittest.main()
