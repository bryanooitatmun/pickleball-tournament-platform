import pytest
from flask import url_for
from app import create_app, db
from app.models import TournamentTier, TournamentFormat, CategoryType, MatchStage, TournamentStatus
from app.organizer.forms import TournamentForm, CategoryForm, MatchForm
from app.player.forms import RegistrationForm, ProfileForm
from app.player.feedback_forms import FeedbackForm
from app.auth.forms import LoginForm, RegistrationForm as UserRegistrationForm
from datetime import date, timedelta, datetime, time

def test_login_form_validation(init_database, app):
    """Test login form validation"""
    with app.test_request_context():
        # Test valid form data
        form = LoginForm(
            email="test@example.com",
            password="testpassword",
            remember_me=True
        )
        assert form.validate() is True
        
        # Test missing username
        form = LoginForm(
            email="",
            password="testpassword"
        )
        assert form.validate() is False
        assert "This field is required." in form.email.errors
        
        # Test missing password
        form = LoginForm(
            email="test@example.com",
            password=""
        )
        assert form.validate() is False
        assert "This field is required." in form.password.errors

def test_user_registration_form_validation(init_database, app):
    """Test user registration form validation"""
    with app.test_request_context():
        # Test valid form data
        form = UserRegistrationForm(
            username="newuser",
            email="newuser@example.com",
            password="Password123",
            password2="Password123"
        )
        assert form.validate() is True
        
        # Test password mismatch
        form = UserRegistrationForm(
            username="newuser",
            email="newuser@example.com",
            password="Password123",
            password2="DifferentPassword"
        )
        assert form.validate() is False
        assert "Field must be equal to password." in form.password2.errors
        
        # Test invalid email format
        form = UserRegistrationForm(
            username="newuser",
            email="invalid-email",
            password="Password123",
            password2="Password123"
        )
        assert form.validate() is False
        assert "Invalid email address." in form.email.errors
        
        # Test username too short
        form = UserRegistrationForm(
            username="nu",  # Too short
            email="newuser@example.com",
            password="Password123",
            password2="Password123"
        )
        assert form.validate() is False
        assert form.username.errors  # Should have errors on username field

def test_tournament_form_validation(init_database, app):
    """Test tournament form validation"""
    with app.test_request_context():
        # Test valid form data
        tomorrow = date.today() + timedelta(days=1)
        next_week = date.today() + timedelta(days=7)
        
        form = TournamentForm(
            name="Test Tournament",
            location="Test Venue",
            description="A test tournament",
            start_date=datetime.combine(tomorrow, time()),  # Convert to datetime
            end_date=datetime.combine(next_week, time()),   # Convert to datetime
            registration_deadline=datetime.combine(date.today(), time()),  # Convert to datetime
            tier=TournamentTier.OPEN.name,  # Use name not value
            format=TournamentFormat.SINGLE_ELIMINATION.name,  # Use name not value
            status=TournamentStatus.UPCOMING.name,  # Add missing required field
            prize_pool=1000.00
        )
        assert form.validate() is True
        
        # Test end date before start date
        form = TournamentForm(
            name="Test Tournament",
            location="Test Venue",
            description="A test tournament",
            start_date=datetime.combine(next_week, time()),   # Start date after end date
            end_date=datetime.combine(tomorrow, time()),
            registration_deadline=datetime.combine(date.today(), time()),
            tier=TournamentTier.OPEN.name,
            format=TournamentFormat.SINGLE_ELIMINATION.name,
            status=TournamentStatus.UPCOMING.name,  # Add missing required field
            prize_pool=1000.00
        )

        assert form.validate() is False
        assert "End date must be after start date." in form.end_date.errors
        
        # Test invalid prize pool (negative)
        form = TournamentForm(
            name="Test Tournament",
            location="Test Venue",
            description="A test tournament",
            start_date=datetime.combine(tomorrow, time()),
            end_date=datetime.combine(next_week, time()), 
            registration_deadline=datetime.combine(date.today(), time()),
            tier=TournamentTier.OPEN.name,
            format=TournamentFormat.SINGLE_ELIMINATION.name,
            status=TournamentStatus.UPCOMING.name,  # Add missing required field
            prize_pool=-100.00  # Negative prize pool
        )
        assert form.validate() is False
        assert form.prize_pool.errors  # Should have errors on prize_pool field

def test_category_form_validation(init_database, app):
    """Test category form validation"""
    with app.test_request_context():
        # Test valid form data
        form = CategoryForm(
            name="Men's Singles A",
            category_type=CategoryType.MENS_SINGLES.name,
            max_participants=32,
            points_awarded=100,
            registration_fee=50.00
        )
        assert form.validate() is True
        
        # Test invalid max participants (negative)
        form = CategoryForm(
            name="Men's Singles A",
            category_type=CategoryType.MENS_SINGLES.name,
            max_participants=-8,  # Negative value
            points_awarded=100,
            registration_fee=50.00
        )
        assert form.validate() is False
        assert form.max_participants.errors  # Should have errors
        
        # Test invalid registration fee (negative)
        form = CategoryForm(
            name="Men's Singles A",
            category_type=CategoryType.MENS_SINGLES.name,
            max_participants=32,
            points_awarded=100,
            registration_fee=-10.00  # Negative fee
        )
        assert form.validate() is False
        assert form.registration_fee.errors  # Should have errors

def test_match_form_validation(init_database, app):
    """Test match form validation"""
    with app.test_request_context():
        # Test valid form data
        future_time = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        
        form = MatchForm(
            court="Court 1",
            scheduled_time=future_time,
            livestream_url="https://youtube.com/watch?v=12345"
        )
        assert form.validate() is True
        
        # Test invalid livestream URL
        form = MatchForm(
            court="Court 1",
            scheduled_time=future_time,
            livestream_url="invalid-url"  # Invalid URL
        )
        assert form.validate() is False
        assert form.livestream_url.errors  # Should have errors

def test_profile_form_validation(init_database, app):
    """Test player profile form validation"""
    with app.test_request_context():
        # Test valid form data
        form = ProfileForm(
            full_name="John Smith",
            country="United States",  # Add required field
            city="New York",  # Add this field
            coach_academy="Test Academy",
            instagram="johnsmith",
            facebook="john.smith",
            tiktok="johnsmith",
            xiaohongshu="johnsmith",
            age=5,
            plays='Right-handed'
        )
        form.validate()
        assert form.validate() is True
        
        # Test full name required
        form = ProfileForm(
            full_name="",  # Empty name
        )
        assert form.validate() is False
        assert "This field is required." in form.full_name.errors
        
        
        # Test social media handle validation (if implemented)
        # For example, if Instagram handle must not contain spaces or special characters

def test_feedback_form_validation(init_database, app):
    """Test feedback form validation"""
    with app.test_request_context():
        # Test valid form data
        form = FeedbackForm(
            tournament_id=1,  # Add this field to pass custom validation
            rating=5,  # Integer not string
            comment="Great tournament!",
            is_anonymous=True
        )
        assert form.validate() is True
        
        # Test invalid rating (out of range)
        form = FeedbackForm(
            rating=6,  # Assuming rating is 1-5
            comment="Great tournament!"
        )
        assert form.validate() is False
        assert form.rating.errors  # Should have errors
        
        # Test missing rating
        form = FeedbackForm(
            comment="Great tournament!"
        )
        assert form.validate() is False
        assert "This field is required." in form.rating.errors
