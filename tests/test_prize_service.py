import pytest
from app import db
from app.models import Tournament, TournamentCategory, CategoryType
from app.services.prize_service import PrizeService
from datetime import date, timedelta

# Helper functions to create test data
def create_test_tournament(db_session, prize_pool=10000.0):
    """Create a test tournament with the specified prize pool"""
    t = Tournament(
        name="Test Tournament",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=2),
        registration_deadline=date.today() - timedelta(days=1),
        prize_pool=prize_pool
    )
    db_session.add(t)
    db_session.commit()
    return t

def create_test_category(db_session, tournament, name, prize_percentage=25.0):
    """Create a test category with the specified name and prize percentage"""
    c = TournamentCategory(
        tournament_id=tournament.id,
        name=name,
        category_type=CategoryType.MENS_SINGLES if "Men's" in name else 
                    CategoryType.WOMENS_SINGLES if "Women's" in name else
                    CategoryType.MENS_DOUBLES if "Men's Doubles" in name else
                    CategoryType.WOMENS_DOUBLES if "Women's Doubles" in name else
                    CategoryType.MIXED_DOUBLES if "Mixed Doubles" in name else
                    CategoryType.CUSTOM,
        max_participants=16,
        prize_percentage=prize_percentage
    )
    db_session.add(c)
    db_session.commit()
    return c

# --- Tests for PrizeService ---

def test_distribute_prize_pool_exact_100_percent(init_database):
    """Test distributing prize pool when percentages add up to exactly 100%"""
    # Setup
    tournament = create_test_tournament(init_database.session, prize_pool=10000.0)
    
    # Create categories with percentages that add up to 100%
    cat1 = create_test_category(init_database.session, tournament, "Men's Singles", prize_percentage=30.0)
    cat2 = create_test_category(init_database.session, tournament, "Women's Singles", prize_percentage=30.0)
    cat3 = create_test_category(init_database.session, tournament, "Mixed Doubles", prize_percentage=40.0)
    
    # Test
    categories = PrizeService.distribute_prize_pool(tournament.id)
    
    # Assert
    # Should have 3 categories
    assert len(categories) == 3
    
    # Find each category in the result
    cat1_result = next((c for c in categories if c.id == cat1.id), None)
    cat2_result = next((c for c in categories if c.id == cat2.id), None)
    cat3_result = next((c for c in categories if c.id == cat3.id), None)
    
    # Verify prize money calculations
    assert cat1_result.prize_money == 3000.0  # 30% of 10000
    assert cat2_result.prize_money == 3000.0  # 30% of 10000
    assert cat3_result.prize_money == 4000.0  # 40% of 10000
    
    # Verify percentages remain unchanged
    assert cat1_result.prize_percentage == 30.0
    assert cat2_result.prize_percentage == 30.0
    assert cat3_result.prize_percentage == 40.0
    
    # Verify sum equals the total prize pool
    total_prize_money = sum(cat.prize_money for cat in categories)
    assert total_prize_money == tournament.prize_pool

def test_distribute_prize_pool_less_than_100_percent(init_database):
    """Test distributing prize pool when percentages add up to less than 100%"""
    # Setup
    tournament = create_test_tournament(init_database.session, prize_pool=10000.0)
    
    # Create categories with percentages that add up to 80%
    cat1 = create_test_category(init_database.session, tournament, "Men's Singles", prize_percentage=30.0)
    cat2 = create_test_category(init_database.session, tournament, "Women's Singles", prize_percentage=20.0)
    cat3 = create_test_category(init_database.session, tournament, "Mixed Doubles", prize_percentage=30.0)
    
    # Test
    categories = PrizeService.distribute_prize_pool(tournament.id)
    
    # Assert
    # Should have 3 categories
    assert len(categories) == 3
    
    # Find each category in the result
    cat1_result = next((c for c in categories if c.id == cat1.id), None)
    cat2_result = next((c for c in categories if c.id == cat2.id), None)
    cat3_result = next((c for c in categories if c.id == cat3.id), None)
    
    # Verify percentages adjusted (scaled up)
    # 30 / 80 * 100 = 37.5%, 20 / 80 * 100 = 25%, 30 / 80 * 100 = 37.5%
    assert round(cat1_result.prize_percentage, 1) == 37.5
    assert round(cat2_result.prize_percentage, 1) == 25.0
    assert round(cat3_result.prize_percentage, 1) == 37.5
    
    # Verify prize money calculations
    assert cat1_result.prize_money == 3750.0  # 37.5% of 10000
    assert cat2_result.prize_money == 2500.0  # 25% of 10000
    assert cat3_result.prize_money == 3750.0  # 37.5% of 10000
    
    # Verify sum equals the total prize pool
    total_prize_money = round(sum(cat.prize_money for cat in categories), 2)
    assert total_prize_money == tournament.prize_pool

def test_distribute_prize_pool_more_than_100_percent(init_database):
    """Test distributing prize pool when percentages add up to more than 100%"""
    # Setup
    tournament = create_test_tournament(init_database.session, prize_pool=10000.0)
    
    # Create categories with percentages that add up to 120%
    cat1 = create_test_category(init_database.session, tournament, "Men's Singles", prize_percentage=40.0)
    cat2 = create_test_category(init_database.session, tournament, "Women's Singles", prize_percentage=40.0)
    cat3 = create_test_category(init_database.session, tournament, "Mixed Doubles", prize_percentage=40.0)
    
    # Test
    categories = PrizeService.distribute_prize_pool(tournament.id)
    
    # Assert
    # Should have 3 categories
    assert len(categories) == 3
    
    # Find each category in the result
    cat1_result = next((c for c in categories if c.id == cat1.id), None)
    cat2_result = next((c for c in categories if c.id == cat2.id), None)
    cat3_result = next((c for c in categories if c.id == cat3.id), None)
    
    # Verify percentages adjusted (scaled down)
    # 40 / 120 * 100 = 33.33% for each
    assert round(cat1_result.prize_percentage, 2) == 33.33
    assert round(cat2_result.prize_percentage, 2) == 33.33
    assert round(cat3_result.prize_percentage, 2) == 33.33
    
    # Verify prize money calculations
    assert round(cat1_result.prize_money, 2) == 3333.33  # 33.33% of 10000
    assert round(cat2_result.prize_money, 2) == 3333.33  # 33.33% of 10000
    assert round(cat3_result.prize_money, 2) == 3333.33  # 33.33% of 10000
    
    # Verify sum equals the total prize pool (within rounding error)
    total_prize_money = round(sum(cat.prize_money for cat in categories), 2)
    assert abs(total_prize_money - tournament.prize_pool) < 0.01

def test_distribute_prize_pool_uneven_percentages(init_database):
    """Test distributing prize pool with uneven percentages that need normalization"""
    # Setup
    tournament = create_test_tournament(init_database.session, prize_pool=10000.0)
    
    # Create categories with uneven percentages that add up to 95%
    cat1 = create_test_category(init_database.session, tournament, "Men's Singles", prize_percentage=33.0)
    cat2 = create_test_category(init_database.session, tournament, "Women's Singles", prize_percentage=27.0)
    cat3 = create_test_category(init_database.session, tournament, "Men's Doubles", prize_percentage=20.0)
    cat4 = create_test_category(init_database.session, tournament, "Women's Doubles", prize_percentage=15.0)
    
    # Test
    categories = PrizeService.distribute_prize_pool(tournament.id)
    
    # Assert
    # Should have 4 categories
    assert len(categories) == 4
    
    # Find each category in the result
    cat1_result = next((c for c in categories if c.id == cat1.id), None)
    cat2_result = next((c for c in categories if c.id == cat2.id), None)
    cat3_result = next((c for c in categories if c.id == cat3.id), None)
    cat4_result = next((c for c in categories if c.id == cat4.id), None)
    
    # Verify percentages adjusted (scaled to 100%)
    expected_factor = 100 / 95
    assert round(cat1_result.prize_percentage, 2) == round(33.0 * expected_factor, 2)
    assert round(cat2_result.prize_percentage, 2) == round(27.0 * expected_factor, 2)
    assert round(cat3_result.prize_percentage, 2) == round(20.0 * expected_factor, 2)
    assert round(cat4_result.prize_percentage, 2) == round(15.0 * expected_factor, 2)
    
    # Verify prize money calculations
    assert round(cat1_result.prize_money, 2) == round(10000.0 * (33.0 * expected_factor / 100), 2)
    assert round(cat2_result.prize_money, 2) == round(10000.0 * (27.0 * expected_factor / 100), 2)
    assert round(cat3_result.prize_money, 2) == round(10000.0 * (20.0 * expected_factor / 100), 2)
    assert round(cat4_result.prize_money, 2) == round(10000.0 * (15.0 * expected_factor / 100), 2)
    
    # Verify sum equals the total prize pool (within rounding error)
    total_prize_money = round(sum(cat.prize_money for cat in categories), 2)
    assert abs(total_prize_money - tournament.prize_pool) < 0.01

def test_distribute_prize_pool_zero_prize_pool(init_database):
    """Test distributing prize pool when tournament has zero prize pool"""
    # Setup
    tournament = create_test_tournament(init_database.session, prize_pool=0.0)
    
    # Create categories
    cat1 = create_test_category(init_database.session, tournament, "Men's Singles", prize_percentage=50.0)
    cat2 = create_test_category(init_database.session, tournament, "Women's Singles", prize_percentage=50.0)
    
    # Test
    categories = PrizeService.distribute_prize_pool(tournament.id)
    
    # Assert
    # Should have 2 categories
    assert len(categories) == 2
    
    # Find each category in the result
    cat1_result = next((c for c in categories if c.id == cat1.id), None)
    cat2_result = next((c for c in categories if c.id == cat2.id), None)
    
    # Percentages should be unchanged
    assert cat1_result.prize_percentage == 50.0
    assert cat2_result.prize_percentage == 50.0
    
    # Prize money should be zero
    assert cat1_result.prize_money == 0.0
    assert cat2_result.prize_money == 0.0

def test_distribute_prize_pool_no_categories(init_database):
    """Test distributing prize pool when tournament has no categories"""
    # Setup
    tournament = create_test_tournament(init_database.session, prize_pool=10000.0)
    
    # Test
    categories = PrizeService.distribute_prize_pool(tournament.id)
    
    # Assert
    # Should have no categories
    assert len(categories) == 0
