import pytest
import os
import tempfile
from app import create_app, db
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:' # Use in-memory SQLite for tests
    WTF_CSRF_ENABLED = False # Disable CSRF for easier form testing
    LOGIN_DISABLED = False # Ensure login is enabled unless specifically disabled in a test
    SERVER_NAME = 'localhost.localdomain' # Required for url_for outside of request context
    SOCKETIO_CORS_ALLOWED_ORIGINS = '*'

@pytest.fixture(scope='session')
def app():
    """Session-wide test Flask application."""
    app = create_app(config_class=TestConfig)
    app_context = app.app_context()
    app_context.push()

    yield app # provide the app object to the tests

    app_context.pop()


@pytest.fixture(scope='function')
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()


@pytest.fixture(scope='function')
def init_database(app):
    """Fixture to initialize the database for each test function."""
    db.create_all()

    yield db # provide the database instance to the test function

    db.session.remove() # Ensure session is closed
    db.drop_all()
