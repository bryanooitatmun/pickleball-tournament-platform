from datetime import datetime
from sqlalchemy import Enum, Table, Column, Integer, ForeignKey, String, Boolean, DateTime, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON
from app import db
from app.models.enums import TournamentTier, TournamentFormat, TournamentStatus, CategoryType, PrizeType # Import necessary enums

# Association table for player partnerships (for doubles)
# Defined here as it links players (user_models) to categories (tournament_models)
partnerships = db.Table('partnerships',
    db.Column('partnership_id', db.Integer, primary_key=True),
    db.Column('player1_id', db.Integer, db.ForeignKey('player_profile.id')),
    db.Column('player2_id', db.Integer, db.ForeignKey('player_profile.id')),
    db.Column('category_id', db.Integer, db.ForeignKey('tournament_category.id'))
)

class Tournament(db.Model):
    __tablename__ = 'tournament'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    organizer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    location = db.Column(db.String(200)) # Consider linking to Venue model instead/as well
    description = db.Column(db.Text)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    registration_deadline = db.Column(db.DateTime)
    tier = db.Column(Enum(TournamentTier), default=TournamentTier.OPEN)
    format = db.Column(Enum(TournamentFormat), default=TournamentFormat.SINGLE_ELIMINATION)
    status = db.Column(Enum(TournamentStatus), default=TournamentStatus.UPCOMING)
    prize_pool = db.Column(db.Float)
    logo = db.Column(db.String(255))
    banner = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    venue_id = db.Column(db.Integer, db.ForeignKey('venue.id'), nullable=True)
    is_featured = db.Column(db.Boolean, default=False)
    featured_image = db.Column(db.String(255))

    is_ranked = db.Column(db.Boolean, default=False) # Should points be awarded?

    total_cash_prize = db.Column(db.Float, default=0.0)  # Total cash across all categories
    total_prize_value = db.Column(db.Float, default=0.0)  # Including merchandise value
    prize_structure_description = db.Column(db.Text, nullable=True)  # Tournament-wide description

    # Payment details
    payment_bank_name = db.Column(db.String(100), nullable=True)
    payment_account_number = db.Column(db.String(50), nullable=True)
    payment_account_name = db.Column(db.String(100), nullable=True)
    payment_reference_prefix = db.Column(db.String(20), nullable=True)
    payment_qr_code = db.Column(db.String(255), nullable=True)
    payment_instructions = db.Column(db.Text, nullable=True)

    # Door gifts
    door_gifts = db.Column(db.Text, nullable=True)
    door_gifts_image = db.Column(db.String(255), nullable=True)

    # Relationships (use strings)
    categories = db.relationship('TournamentCategory', backref='tournament', lazy='dynamic', cascade='all, delete-orphan')
    support_tickets = db.relationship('SupportTicket', backref='tournament', lazy='dynamic')
    # organizer relationship defined in User model via backref
    # venue relationship defined in Venue model via backref
    # platform_sponsors relationship defined via secondary table 'tournament_sponsors'

    def is_completed(self):
        return self.status == TournamentStatus.COMPLETED

    @property
    def prize_summary(self):
        """Get overall prize summary statistics"""
        # Ensure categories are loaded if accessed this way
        cats = self.categories.all()
        return {
            'total_cash': self.total_cash_prize,
            'total_value': self.total_prize_value,
            'merchandise_value': self.total_prize_value - self.total_cash_prize,
            'category_count': len(cats),
            'has_merchandise': any(cat.has_merchandise for cat in cats),
            'has_trophies': any(cat.has_trophies for cat in cats)
        }

    @property
    def winners_by_category(self):
        """Return a dictionary of winners for each category in this tournament."""
        # This requires Match model, consider moving to a service layer or keeping but ensuring Match is imported
        from app.models.match_models import Match # Local import to avoid circular dependency at module level

        if self.status != TournamentStatus.COMPLETED:
            return {}

        result = {}
        for category in self.categories:
            category_results = {}

            # Find the final match (round 1) for this category
            final_match = Match.query.filter_by(
                category_id=category.id,
                round=1
            ).first()

            if final_match:
                is_doubles = category.category_type in [
                    CategoryType.MENS_DOUBLES,
                    CategoryType.WOMENS_DOUBLES,
                    CategoryType.MIXED_DOUBLES
                ]

                # Get winners (1st place)
                if is_doubles:
                    if final_match.winner:
                        category_results[1] = [
                            final_match.winner.player1,
                            final_match.winner.player2
                        ]
                else:
                    if final_match.winner:
                        category_results[1] = final_match.winner

                # Get runners-up (2nd place)
                if is_doubles:
                    if final_match.loser:
                        category_results[2] = [
                            final_match.loser.player1,
                            final_match.loser.player2
                        ]
                else:
                    if final_match.loser:
                        category_results[2] = final_match.loser

                # TODO: Handle semifinalists (3rd/4th place) - requires querying previous rounds or playoff matches

            # Only add categories that have winners
            if category_results:
                result[category.category_type.value] = category_results

        return result

    def is_registration_open(self):
        # Ensure registration_deadline is not None before comparing
        return self.registration_deadline and datetime.utcnow() < self.registration_deadline

    def __repr__(self):
        return f'<Tournament {self.name}>'


class TournamentCategory(db.Model):
    __tablename__ = 'tournament_category'
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'))
    category_type = db.Column(Enum(CategoryType))
    name = db.Column(db.String(100)) # Allow custom names
    max_participants = db.Column(db.Integer)
    points_awarded = db.Column(db.Integer) # Base points for the winner
    format = db.Column(Enum(TournamentFormat), nullable=True) # Allow override from tournament default
    registration_fee = db.Column(db.Float, default=0.0)
    description = db.Column(db.Text)

    # display order field (lower number = higher priority)
    display_order = db.Column(db.Integer, default=999)

    # Prize money details
    prize_percentage = db.Column(db.Float, default=0)  # Percentage of total tournament prize pool
    prize_money = db.Column(db.Float, default=0.0)  # Total cash prize for this category (can be calculated or set directly)
    prize_image = db.Column(db.String(255), nullable=True) # Image representing prizes for this category

    has_merchandise = db.Column(db.Boolean, default=False)  # Quick flag for filtering
    has_trophies = db.Column(db.Boolean, default=False)  # Quick flag for filtering
    prize_summary = db.Column(db.Text, nullable=True)  # Brief overview for display

    total_prize_value = db.Column(db.Float, default=0.0) # Calculated total value (cash + merchandise)

    # Category restrictions
    min_dupr_rating = db.Column(db.Float, nullable=True)
    max_dupr_rating = db.Column(db.Float, nullable=True)
    min_age = db.Column(db.Integer, nullable=True)
    max_age = db.Column(db.Integer, nullable=True)
    gender_restriction = db.Column(db.String(20), nullable=True)  # 'male', 'female', 'mixed', or None

    # Format-specific settings
    group_count = db.Column(db.Integer, default=0)  # Number of groups in group stage
    teams_per_group = db.Column(db.Integer, default=0)  # Teams per group
    teams_advancing_per_group = db.Column(db.Integer, default=0)  # Teams advancing to knockout

    # Custom point distribution as JSON
    # Structure: {"1": 100, "2": 70, "3-4": 50, "5-8": 25, etc.} (Percentages of points_awarded)
    points_distribution = db.Column(JSON, default={})

    # Custom prize distribution as JSON
    # Structure: {"1": 50, "2": 25, "3-4": 12.5, "5-8": 6.25, etc.} (Percentages of prize_money)
    prize_distribution = db.Column(JSON, default={})

    # Relationships (use strings)
    registrations = db.relationship('Registration', backref='category', lazy='dynamic', cascade='all, delete-orphan')
    matches = db.relationship('Match', backref='category', lazy='dynamic', cascade='all, delete-orphan')
    groups = db.relationship('Group', backref='category', lazy='dynamic', cascade='all, delete-orphan')
    prizes = db.relationship('Prize', backref='category', lazy='dynamic', cascade='all, delete-orphan')
    # teams relationship defined in Team model via backref

    def is_doubles(self):
        return self.category_type in [
            CategoryType.MENS_DOUBLES,
            CategoryType.WOMENS_DOUBLES,
            CategoryType.MIXED_DOUBLES
        ]

    def calculate_prize_money(self):
        """Calculate prize money as the sum of all cash prizes in this category"""
        from app.models.prize_models import PrizeType
        
        # Get all cash prizes for this category
        cash_prizes = self.prizes.filter_by(prize_type=PrizeType.CASH).all()
        
        # Sum up all cash amounts (handle None values)
        self.prize_money = sum(prize.cash_amount or 0.0 for prize in cash_prizes)
        
        return self.prize_money

    def get_points_for_place(self, place):
        """Get points for a specific place based on distribution"""
        if not self.points_distribution:
            # Default distribution if none set
            return self._default_points_for_place(place)

        # Find the matching place in the distribution
        for place_range, percentage in self.points_distribution.items():
            if self._is_in_place_range(place, place_range):
                # Ensure points_awarded and percentage are not None
                if self.points_awarded is not None and percentage is not None:
                     return int(self.points_awarded * (percentage / 100))
                else:
                    return 0 # Or handle error appropriately
        return 0

    def get_prize_for_place(self, place):
        """Get prize money for a specific place based on distribution"""
        if not self.prize_distribution:
            # Default distribution if none set
            return self._default_prize_for_place(place)

        # Find the matching place in the distribution
        for place_range, percentage in self.prize_distribution.items():
            if self._is_in_place_range(place, place_range):
                 # Ensure prize_money and percentage are not None
                if self.prize_money is not None and percentage is not None:
                    return self.prize_money * (percentage / 100)
                else:
                    return 0.0 # Or handle error appropriately
        return 0.0

    def calculate_prize_values(self):
        """Calculate and update prize values based on defined prizes"""
        from app.models.prize_models import PrizeType
        
        # Calculate cash prize (sum of all cash prizes)
        cash_prizes = self.prizes.filter_by(prize_type=PrizeType.CASH).all()
        self.prize_money = sum(p.cash_amount or 0.0 for p in cash_prizes)
        
        # Calculate merchandise value (sum of monetary value * quantity for non-cash prizes)
        non_cash_prizes = [p for p in self.prizes.all() if p.prize_type != PrizeType.CASH]
        merch_value = sum((p.monetary_value or 0.0) * (p.quantity or 1) for p in non_cash_prizes)
        
        # Calculate total prize value
        self.total_prize_value = self.prize_money + merch_value
        
        # Update flags
        current_prizes = self.prizes.all()
        self.has_merchandise = any(p.prize_type == PrizeType.MERCHANDISE for p in current_prizes)
        
        # Calculate prize percentage if we have a tournament with a non-zero total cash prize
        if self.tournament and self.tournament.total_cash_prize and self.tournament.total_cash_prize > 0:
            self.prize_percentage = (self.prize_money / self.tournament.total_cash_prize) * 100
        else:
            self.prize_percentage = 0
            
        return self.total_prize_value

    def add_merchandise_prize(self, placement, title, value, description=None, image=None, quantity=1):
        """Add a merchandise prize to this category"""
        # Import Prize locally if needed
        from app.models.prize_models import Prize
        prize = Prize(
            category_id=self.id,
            placement=placement,
            prize_type=PrizeType.MERCHANDISE,
            title=title,
            description=description,
            image=image,
            monetary_value=value,
            quantity=quantity
        )
        db.session.add(prize)
        self.has_merchandise = True # Update flag
        # Consider recalculating total_prize_value here or deferring
        return prize

    def _is_in_place_range(self, place, place_range):
        """Check if a place is within a range like '1', '2', '3-4', '5-8', etc."""
        try:
            if '-' in place_range:
                start, end = map(int, place_range.split('-'))
                return start <= place <= end
            else:
                return place == int(place_range)
        except ValueError:
            # Handle cases where place_range is not a valid number or range
            return False


    def _default_points_for_place(self, place):
        """Default points distribution if none specified"""
        base_points = self.points_awarded or 0
        if place == 1:
            return base_points
        elif place == 2:
            return int(base_points * 0.7)
        elif place <= 4:
            return int(base_points * 0.5)
        elif place <= 8:
            return int(base_points * 0.25)
        elif place <= 16:
            return int(base_points * 0.15)
        return 0

    def _default_prize_for_place(self, place):
        """Default prize distribution if none specified"""
        base_prize = self.prize_money or 0.0
        if place == 1:
            return base_prize * 0.5
        elif place == 2:
            return base_prize * 0.25
        elif place <= 4:
            return base_prize * 0.125
        elif place <= 8:
            return base_prize * 0.0625
        return 0.0

    @property
    def grouped_prizes(self):
        """Group prizes by placement for easy display"""
        result = {}
        # Ensure self.prizes is loaded if accessed this way
        for prize in self.prizes.all():
            if prize.placement not in result:
                result[prize.placement] = []
            result[prize.placement].append(prize)
        # Sort placements if needed, e.g., numerically/logically
        # sorted_result = {k: result[k] for k in sorted(result.keys(), key=lambda x: int(x.split('-')[0]))}
        return result

    def __repr__(self):
        return f'<TournamentCategory {self.name} ({self.category_type.value})>'