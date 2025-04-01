import pytest
from datetime import date, timedelta, datetime
from app.models import Tournament, TournamentStatus

# --- Unit Tests for Tournament Model ---

def test_tournament_is_registration_open_true():
    """Test is_registration_open() returns True when within deadline."""
    today = datetime.utcnow().date()
    tournament = Tournament(
        name="Reg Open",
        status=TournamentStatus.UPCOMING,
        registration_deadline=today + timedelta(days=1) # Deadline is tomorrow
    )
    assert tournament.is_registration_open() is True

def test_tournament_is_registration_open_false_past_deadline():
    """Test is_registration_open() returns False when deadline has passed."""
    today = datetime.utcnow().date()
    tournament = Tournament(
        name="Reg Closed",
        status=TournamentStatus.UPCOMING,
        registration_deadline=today - timedelta(days=1) # Deadline was yesterday
    )
    assert tournament.is_registration_open() is False

def test_tournament_is_registration_open_false_no_deadline():
    """Test is_registration_open() returns False if deadline is None."""
    tournament = Tournament(
        name="No Deadline",
        status=TournamentStatus.UPCOMING,
        registration_deadline=None # No deadline set
    )
    assert tournament.is_registration_open() is False

def test_tournament_is_registration_open_false_not_upcoming():
    """Test is_registration_open() returns False if status is not UPCOMING."""
    today = datetime.utcnow().date()
    # Test ONGOING status
    tournament_ongoing = Tournament(
        name="Ongoing",
        status=TournamentStatus.ONGOING,
        registration_deadline=today + timedelta(days=1) # Deadline hasn't passed
    )
    assert tournament_ongoing.is_registration_open() is False

    # Test COMPLETED status
    tournament_completed = Tournament(
        name="Completed",
        status=TournamentStatus.COMPLETED,
        registration_deadline=today + timedelta(days=1)
    )
    assert tournament_completed.is_registration_open() is False

    # Test CANCELLED status (assuming it exists)
    # tournament_cancelled = Tournament(
    #     name="Cancelled",
    #     status=TournamentStatus.CANCELLED, # Assuming CANCELLED status exists
    #     registration_deadline=today + timedelta(days=1)
    # )
    # assert tournament_cancelled.is_registration_open() is False

def test_tournament_is_registration_open_edge_case_deadline_today():
    """Test is_registration_open() behavior when deadline is exactly today."""
    # The behavior depends on whether the check includes the deadline day.
    # Assuming <= check, deadline today means still open.
    today = datetime.utcnow().date()
    tournament = Tournament(
        name="Deadline Today",
        status=TournamentStatus.UPCOMING,
        registration_deadline=today # Deadline is today
    )
    # The current implementation in the route checks `datetime.utcnow() > self.registration_deadline`.
    # This means if the deadline is set to a date (midnight), registration closes *at the start* of that day.
    # Let's adjust the model method assumption or the test based on desired behavior.
    # Assuming the check should allow registration *on* the deadline day until end of day.
    # A better check might involve comparing dates directly: `date.today() <= self.registration_deadline.date()`
    # For now, testing the *likely* behavior based on route code:
    # If deadline is date object, comparison with datetime.utcnow() might be tricky.
    # Let's assume the check is meant to be inclusive of the deadline day.
    # Re-evaluating: The route code uses `not tournament.is_registration_open()`.
    # Let's assume the model method `is_registration_open` should reflect the logic:
    # open = self.status == TournamentStatus.UPCOMING and self.registration_deadline and datetime.utcnow().date() <= self.registration_deadline
    assert tournament.is_registration_open() is True # Should be true if inclusive

# --- Unit Tests for PlayerProfile Model ---

# Note: Testing properties like matches_won, matches_lost, avg_match_duration
# requires setting up related Match and Team objects. These might be better
# suited for integration tests or require significant mocking if kept as pure unit tests.
# Let's focus on get_points for now, assuming it's a simpler calculation based on profile fields.

def test_player_profile_get_points_no_category():
    """Test get_points() returns the sum of all category points."""
    from app.models import PlayerProfile
    profile = PlayerProfile(
        mens_singles_points=100,
        womens_singles_points=50,
        mens_doubles_points=75,
        womens_doubles_points=25,
        mixed_doubles_points=10
    )
    # Assuming get_points(None) sums all points fields
    assert profile.get_points(None) == 100 + 50 + 75 + 25 + 10

def test_player_profile_get_points_specific_category():
    """Test get_points() returns points for a specific category type."""
    from app.models import PlayerProfile, CategoryType
    profile = PlayerProfile(
        mens_singles_points=100,
        womens_singles_points=50,
        mens_doubles_points=75,
        womens_doubles_points=25,
        mixed_doubles_points=10
    )
    assert profile.get_points(CategoryType.MENS_SINGLES) == 100
    assert profile.get_points(CategoryType.WOMENS_DOUBLES) == 25
    assert profile.get_points(CategoryType.MIXED_DOUBLES) == 10

def test_player_profile_get_points_zero_points():
    """Test get_points() returns 0 when points fields are zero or None."""
    from app.models import PlayerProfile, CategoryType
    profile1 = PlayerProfile() # All points default to 0 or None
    profile2 = PlayerProfile(mens_singles_points=0)

    assert profile1.get_points(None) == 0
    assert profile1.get_points(CategoryType.MENS_SINGLES) == 0
    assert profile2.get_points(None) == 0
    assert profile2.get_points(CategoryType.MENS_SINGLES) == 0

# TODO: Add unit tests for other complex model methods if feasible,
# or consider integration tests for properties relying on relationships (matches_won etc.)