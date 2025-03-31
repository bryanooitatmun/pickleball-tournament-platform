import pytest
from flask import url_for
from app.models import Tournament # Import Tournament model
from datetime import date, timedelta

def test_app_creation(app):
    """Test if the Flask app instance is created."""
    assert app is not None

def test_index_route(client, init_database): # Add init_database fixture here
    """Test if the index route '/' returns a 200 OK status."""
    # init_database fixture ensures tables are created before this runs

    # Create a dummy tournament with ID 1 required by the index route
    # Note: We might need a dummy organizer user as well if the model requires it.
    # Assuming organizer_id is not strictly required or nullable for this basic test.
    dummy_tournament = Tournament(
        id=1, # Explicitly set ID
        name="Test Tournament",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=1),
        registration_deadline=date.today() - timedelta(days=1)
        # Add other required fields with default/dummy values if necessary
    )
    init_database.session.add(dummy_tournament)
    init_database.session.commit()

    response = client.get('/')
    assert response.status_code == 200
    # You could add more assertions here, e.g., checking for specific content
    # assert b"Test Tournament" in response.data # Check if tournament name appears

def test_config(app):
    """Test if the correct configuration is loaded."""
    assert app.config['TESTING'] is True
    assert app.config['SQLALCHEMY_DATABASE_URI'] == 'sqlite:///:memory:'
    assert app.config['WTF_CSRF_ENABLED'] is False
