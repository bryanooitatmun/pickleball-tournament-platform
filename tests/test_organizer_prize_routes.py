import pytest
from flask import url_for, json
from app.models import (User, UserRole, Tournament, TournamentCategory, CategoryType,
                        TournamentFormat, Prize, PrizeType, TournamentStatus)
from tests.test_organizer_tournament_routes import create_test_tournament # Reuse helper
from tests.test_organizer_category_routes import create_test_category # Reuse helper

# --- Helper Functions ---

def create_test_prize(db, category, placement="1", prize_type=PrizeType.CASH, cash_amount=100.0, title=None):
    """Helper to create a prize."""
    prize = Prize(
        category_id=category.id,
        placement=placement,
        prize_type=prize_type,
        cash_amount=cash_amount if prize_type == PrizeType.CASH else None,
        title=title if prize_type == PrizeType.MERCHANDISE else None,
        monetary_value=cash_amount if prize_type == PrizeType.MERCHANDISE else None # Assume value = cash for simplicity here
    )
    db.session.add(prize)
    db.session.commit()
    return prize

# --- Tests for Edit Prizes ---

def test_edit_prizes_get_as_organizer(client, organizer_user, test_db):
    """
    GIVEN a Flask app, organizer, tournament, and categories with prizes
    WHEN the '/organizer/tournament/<id>/edit/prizes' page is requested (GET)
    THEN check the response is valid and shows prize editing forms
    """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)
    category1 = create_test_category(test_db, tournament, name="Category A")
    category2 = create_test_category(test_db, tournament, name="Category B")
    prize1 = create_test_prize(test_db, category1, placement="1", cash_amount=200)
    prize2 = create_test_prize(test_db, category1, placement="2", prize_type=PrizeType.MERCHANDISE, title="Cool Shirt", cash_amount=50) # Use cash_amount as value for helper

    response = client.get(url_for('organizer.edit_prizes', id=tournament.id))

    assert response.status_code == 200
    assert f'Edit Prizes - {tournament.name}'.encode() in response.data
    assert b'Category A' in response.data
    assert b'Category B' in response.data
    # Check existing prize details are shown
    assert b'value="1"' in response.data # Placement
    assert b'value="200.0"' in response.data # Cash amount
    assert b'value="Cool Shirt"' in response.data # Merch title
    assert b'Add Prize' in response.data # Button to add new prizes

def test_edit_prizes_post_add_prize(client, organizer_user, test_db):
    """
    GIVEN a Flask app, organizer, tournament, and category
    WHEN the edit prizes form is submitted (POST) with data for a new prize
    THEN check a new Prize is created and associated with the category
    """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)
    category = create_test_category(test_db, tournament)

    post_data = {
        # New prize fields for the specific category
        f'new_placement_{category.id}': ['1'], # Add 1st place prize
        f'new_prize_type_{category.id}': [PrizeType.CASH.value],
        f'new_cash_amount_{category.id}': ['500.00'],
        f'new_title_{category.id}': [''], # Not needed for cash
        f'new_description_{category.id}': [''],
        f'new_monetary_value_{category.id}': [''],
        f'new_quantity_{category.id}': ['']
    }

    response = client.post(url_for('organizer.edit_prizes', id=tournament.id), data=post_data, follow_redirects=False)

    assert response.status_code == 302 # Redirects to tournament detail page
    assert url_for('organizer.tournament_detail', id=tournament.id) in response.location

    # Verify prize was created
    new_prize = Prize.query.filter_by(category_id=category.id, placement='1').first()
    assert new_prize is not None
    assert new_prize.prize_type == PrizeType.CASH
    assert new_prize.cash_amount == 500.00

    # Verify category totals were updated (assuming calculate_prize_values works)
    test_db.session.refresh(category)
    assert category.prize_money == 500.00
    assert category.total_prize_value == 500.00
    test_db.session.refresh(tournament)
    assert tournament.total_cash_prize == 500.00
    assert tournament.total_prize_value == 500.00


def test_edit_prizes_post_update_prize(client, organizer_user, test_db):
    """
    GIVEN a Flask app, organizer, tournament, category, and existing prize
    WHEN the edit prizes form is submitted (POST) with updated data for the prize
    THEN check the Prize object is updated in the DB
    """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)
    category = create_test_category(test_db, tournament)
    prize = create_test_prize(test_db, category, placement="1", prize_type=PrizeType.CASH, cash_amount=100)

    post_data = {
        # Existing prize fields
        f'prize_id_{category.id}': [str(prize.id)],
        f'placement_{prize.id}': ['1st Place'], # Update placement description
        f'prize_type_{prize.id}': [PrizeType.CASH.value],
        f'cash_amount_{prize.id}': ['150.00'], # Update cash amount
        f'title_{prize.id}': [''],
        f'description_{prize.id}': [''],
        f'monetary_value_{prize.id}': [''],
        f'quantity_{prize.id}': ['']
    }

    response = client.post(url_for('organizer.edit_prizes', id=tournament.id), data=post_data, follow_redirects=False)

    assert response.status_code == 302

    # Verify prize update
    test_db.session.refresh(prize)
    assert prize.placement == '1st Place'
    assert prize.cash_amount == 150.00

    # Verify category/tournament totals updated
    test_db.session.refresh(category)
    assert category.prize_money == 150.00
    test_db.session.refresh(tournament)
    assert tournament.total_cash_prize == 150.00

def test_edit_prizes_post_delete_prize(client, organizer_user, test_db):
    """
    GIVEN a Flask app, organizer, tournament, category, and existing prize
    WHEN the edit prizes form is submitted (POST) with the prize marked for deletion
    THEN check the Prize object is deleted from the DB
    """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)
    category = create_test_category(test_db, tournament)
    prize_to_delete = create_test_prize(test_db, category, placement="1", cash_amount=100)
    prize_id = prize_to_delete.id

    post_data = {
        # Mark prize for deletion
        f'delete_prize_{category.id}': [str(prize_id)]
    }

    response = client.post(url_for('organizer.edit_prizes', id=tournament.id), data=post_data, follow_redirects=False)

    assert response.status_code == 302

    # Verify prize was deleted
    deleted_prize = Prize.query.get(prize_id)
    assert deleted_prize is None

    # Verify category/tournament totals updated
    test_db.session.refresh(category)
    assert category.prize_money == 0.00
    test_db.session.refresh(tournament)
    assert tournament.total_cash_prize == 0.00

def test_edit_prizes_permission_denied(client, organizer_user, other_organizer_user, test_db):
    """ Test organizer cannot edit prizes for another organizer's tournament """
    tournament = create_test_tournament(test_db, other_organizer_user)
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)

    response = client.get(url_for('organizer.edit_prizes', id=tournament.id), follow_redirects=True)
    assert b'You do not have permission to edit prizes for this tournament.' in response.data

# --- Tests for Distribute Prize Money ---

def test_distribute_prize_money_success(client, organizer_user, test_db, mocker):
    """
    GIVEN a Flask app, organizer, tournament with prize pool and categories with percentages
    WHEN the '/organizer/tournament/<id>/distribute_prize_money' route is POSTed to
    THEN check PrizeService is called and success message is flashed
    """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)
    tournament.prize_pool = 1000.00 # Set prize pool
    category1 = create_test_category(test_db, tournament, name="Cat A")
    category1.prize_percentage = 60.0 # 60% of pool
    category2 = create_test_category(test_db, tournament, name="Cat B")
    category2.prize_percentage = 40.0 # 40% of pool
    test_db.session.commit()

    # Mock the PrizeService call
    mock_distribute = mocker.patch('app.organizer.prize_routes.PrizeService.distribute_prize_pool', return_value=[category1, category2])

    response = client.post(url_for('organizer.distribute_prize_money', id=tournament.id), follow_redirects=True) # Follow redirect to check flash

    assert response.status_code == 200 # Back on edit prizes page
    assert b'Prize money distributed among 2 categories' in response.data
    mock_distribute.assert_called_once_with(tournament.id)

def test_distribute_prize_money_no_pool(client, organizer_user, test_db):
    """
    GIVEN a Flask app, organizer, tournament WITHOUT prize pool set
    WHEN the distribute prize money route is POSTed to
    THEN check distribution is blocked and warning message is flashed
    """
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)
    tournament = create_test_tournament(test_db, organizer_user)
    tournament.prize_pool = None # No prize pool
    test_db.session.commit()

    response = client.post(url_for('organizer.distribute_prize_money', id=tournament.id), follow_redirects=True)

    assert response.status_code == 200 # Back on edit prizes page
    assert b'Tournament prize pool must be set to distribute prize money.' in response.data

def test_distribute_prize_money_permission_denied(client, organizer_user, other_organizer_user, test_db):
    """ Test organizer cannot distribute prizes for another organizer's tournament """
    tournament = create_test_tournament(test_db, other_organizer_user)
    tournament.prize_pool = 500.00
    test_db.session.commit()
    client.post(url_for('auth.login'), data={'email': organizer_user.email, 'password': 'password'}, follow_redirects=True)

    response = client.post(url_for('organizer.distribute_prize_money', id=tournament.id), follow_redirects=True)
    assert b'You do not have permission to manage this tournament.' in response.data