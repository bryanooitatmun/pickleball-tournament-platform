import pytest
from flask import current_app
from unittest.mock import patch
from app.helpers.tournament import _generate_cross_group_seeding

# --- Unit Tests for _generate_cross_group_seeding ---

def test_cross_group_seeding_4_groups_2_advancing():
    """Test the 4 groups, 2 advancing scenario."""
    advancing_participants = [
        {'team': 'T_A1', 'group': 'A', 'position': 1, 'code': 'A1'},
        {'team': 'T_A2', 'group': 'A', 'position': 2, 'code': 'A2'},
        {'team': 'T_B1', 'group': 'B', 'position': 1, 'code': 'B1'},
        {'team': 'T_B2', 'group': 'B', 'position': 2, 'code': 'B2'},
        {'team': 'T_C1', 'group': 'C', 'position': 1, 'code': 'C1'},
        {'team': 'T_C2', 'group': 'C', 'position': 2, 'code': 'C2'},
        {'team': 'T_D1', 'group': 'D', 'position': 1, 'code': 'D1'},
        {'team': 'T_D2', 'group': 'D', 'position': 2, 'code': 'D2'},
    ]
    num_groups = 4
    teams_per_group = 2

    seeded = _generate_cross_group_seeding(advancing_participants, num_groups, teams_per_group)

    # P1 = [A1, B1, C1, D1]
    # P2 = [A2, B2, C2, D2]
    # Pairing P1 vs P2: A1 vs D2, B1 vs C2, C1 vs B2, D1 vs A2
    # Expected flattened order: A1, D2, B1, C2, C1, B2, D1, A2
    expected_codes = ['A1', 'D2', 'B1', 'C2', 'C1', 'B2', 'D1', 'A2']
    assert len(seeded) == 8
    for i, code in enumerate(expected_codes):
        assert seeded[i]['code'] == code, f"Mismatch at index {i}"

def test_cross_group_seeding_8_groups_2_advancing():
    """Test 8 groups, 2 advancing scenario."""
    advancing_participants = []
    for g in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']:
        advancing_participants.append({'team': f'T_{g}1', 'group': g, 'position': 1, 'code': f'{g}1'})
        advancing_participants.append({'team': f'T_{g}2', 'group': g, 'position': 2, 'code': f'{g}2'})

    num_groups = 8
    teams_per_group = 2

    seeded = _generate_cross_group_seeding(advancing_participants, num_groups, teams_per_group)

    # P1 = [A1..H1], P2 = [A2..H2]
    # Pairing P1 vs P2: A1 vs H2, B1 vs G2, C1 vs F2, D1 vs E2, E1 vs D2, F1 vs C2, G1 vs B2, H1 vs A2
    # Expected flattened order: A1, H2, B1, G2, C1, F2, D1, E2, E1, D2, F1, C2, G1, B2, H1, A2
    expected_codes = ['A1', 'H2', 'B1', 'G2', 'C1', 'F2', 'D1', 'E2', 'E1', 'D2', 'F1', 'C2', 'G1', 'B2', 'H1', 'A2']
    assert len(seeded) == 16
    for i, code in enumerate(expected_codes):
        assert seeded[i]['code'] == code, f"Mismatch at index {i}"

def test_cross_group_seeding_4_groups_3_advancing():
    """Test the 4 groups, 3 advancing scenario."""
    advancing_participants = []
    for g in ['A', 'B', 'C', 'D']:
        for p in [1, 2, 3]:
            advancing_participants.append({'team': f'T_{g}{p}', 'group': g, 'position': p, 'code': f'{g}{p}'})

    num_groups = 4
    teams_per_group = 3

    seeded = _generate_cross_group_seeding(advancing_participants, num_groups, teams_per_group)

    # P1 = [A1, B1, C1, D1]
    # P2 = [A2, B2, C2, D2]
    # P3 = [A3, B3, C3, D3]
    # Pairing P1 vs P3: A1 vs D3, B1 vs C3, C1 vs B3, D1 vs A3
    # Pairing P2 vs P2: A2 vs D2, B2 vs C2
    # Expected flattened order: A1, D3, B1, C3, C1, B3, D1, A3, A2, D2, B2, C2
    expected_codes = ['A1', 'D3', 'B1', 'C3', 'C1', 'B3', 'D1', 'A3', 'A2', 'D2', 'B2', 'C2']
    assert len(seeded) == 12
    for i, code in enumerate(expected_codes):
        assert seeded[i]['code'] == code, f"Mismatch at index {i}"

def test_cross_group_seeding_empty_input():
    """Test with empty participant list."""
    seeded = _generate_cross_group_seeding([], 4, 2)
    assert seeded == []

def test_cross_group_seeding_fewer_participants_than_expected():
    """Test with fewer participants - uses None padding."""
    advancing_participants = [
        {'team': 'T_A1', 'group': 'A', 'position': 1, 'code': 'A1'},
        {'team': 'T_A2', 'group': 'A', 'position': 2, 'code': 'A2'},
        {'team': 'T_B1', 'group': 'B', 'position': 1, 'code': 'B1'},
        # Missing B2
        {'team': 'T_C1', 'group': 'C', 'position': 1, 'code': 'C1'},
        {'team': 'T_C2', 'group': 'C', 'position': 2, 'code': 'C2'},
        {'team': 'T_D1', 'group': 'D', 'position': 1, 'code': 'D1'},
        # Missing D2
    ]
    num_groups = 4
    teams_per_group = 2

    seeded = _generate_cross_group_seeding(advancing_participants, num_groups, teams_per_group)

    # P1 = [A1, B1, C1, D1]
    # P2 = [A2, None, C2, None] (padded)
    # Pairing P1 vs P2: A1 vs None(D2), B1 vs C2, C1 vs None(B2), D1 vs A2
    # Expected flattened: A1, None, B1, C2, C1, None, D1, A2
    expected_codes = ['A1', None, 'B1', 'C2', 'C1', None, 'D1', 'A2']
    assert len(seeded) == 8
    for i, code in enumerate(expected_codes):
        if code is None:
            assert seeded[i] is None, f"Expected None at index {i}"
        else:
            assert seeded[i]['code'] == code, f"Mismatch at index {i}"

def test_cross_group_seeding_2_groups_4_advancing():
    """Test 2 groups, 4 advancing scenario."""
    advancing_participants = []
    for g in ['A', 'B']:
        for p in [1, 2, 3, 4]:
            advancing_participants.append({'team': f'T_{g}{p}', 'group': g, 'position': p, 'code': f'{g}{p}'})

    num_groups = 2
    teams_per_group = 4

    seeded = _generate_cross_group_seeding(advancing_participants, num_groups, teams_per_group)

    # P1=[A1,B1], P2=[A2,B2], P3=[A3,B3], P4=[A4,B4]
    # Pair P1 vs P4: A1 vs B4, B1 vs A4
    # Pair P2 vs P3: A2 vs B3, B2 vs A3
    # Expected flattened: A1, B4, B1, A4, A2, B3, B2, A3
    expected_codes = ['A1', 'B4', 'B1', 'A4', 'A2', 'B3', 'B2', 'A3']
    assert len(seeded) == 8
    for i, code in enumerate(expected_codes):
        assert seeded[i]['code'] == code, f"Mismatch at index {i}"