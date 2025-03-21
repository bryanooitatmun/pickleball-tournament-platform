from datetime import datetime
from flask_login import UserMixin
from flask import current_app
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login
import enum
from sqlalchemy import Enum, Table, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON

class UserRole(enum.Enum):
    ADMIN = "admin"
    PLAYER = "player"
    ORGANIZER = "organizer"

class TournamentTier(enum.Enum):
    SLATE = "SLATE"
    CUP = "CUP"
    OPEN = "OPEN"
    CHALLENGE = "CHALLENGE"

class TournamentFormat(enum.Enum):
    SINGLE_ELIMINATION = "Single Elimination"
    DOUBLE_ELIMINATION = "Double Elimination"
    ROUND_ROBIN = "Round Robin"
    GROUP_KNOCKOUT = "Group Stage + Knockout"

class TournamentStatus(enum.Enum):
    UPCOMING = "upcoming"
    ONGOING = "ongoing"
    COMPLETED = "completed"

class CategoryType(enum.Enum):
    MENS_SINGLES = "Men's Singles"
    WOMENS_SINGLES = "Women's Singles"
    MENS_DOUBLES = "Men's Doubles"
    WOMENS_DOUBLES = "Women's Doubles"
    MIXED_DOUBLES = "Mixed Doubles"
    # For custom categories
    CUSTOM = "Custom Category"

class MatchStage(enum.Enum):
    GROUP = "group"
    KNOCKOUT = "knockout"
    PLAYOFF = "playoff"  # For 3rd place matches, etc.


# Association table for player partnerships (for doubles)
partnerships = db.Table('partnerships',
    db.Column('partnership_id', db.Integer, primary_key=True),
    db.Column('player1_id', db.Integer, db.ForeignKey('player_profile.id')),
    db.Column('player2_id', db.Integer, db.ForeignKey('player_profile.id')),
    db.Column('category_id', db.Integer, db.ForeignKey('tournament_category.id'))
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100))
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(Enum(UserRole), default=UserRole.PLAYER)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    player_profile = db.relationship('PlayerProfile', backref='user', uselist=False)
    tournaments_organized = db.relationship('Tournament', backref='organizer', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == UserRole.ADMIN
    
    def is_organizer(self):
        return self.role == UserRole.ORGANIZER or self.role == UserRole.ADMIN
    
    def is_player(self):
        return self.role == UserRole.PLAYER

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class PlayerProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    full_name = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(100))
    city = db.Column(db.String(100))
    age = db.Column(db.Integer)
    bio = db.Column(db.Text)
    plays = db.Column(db.String(50))  # Right-handed, Left-handed
    height = db.Column(db.String(20))  # Height in ft and inches
    paddle = db.Column(db.String(100))  # Paddle model they use
    profile_image = db.Column(db.String(255))
    action_image = db.Column(db.String(255))
    banner_image = db.Column(db.String(255))
    instagram = db.Column(db.String(255))
    facebook = db.Column(db.String(255))
    twitter = db.Column(db.String(255))
    turned_pro = db.Column(db.Integer)
    
    # Rankings
    mens_singles_points = db.Column(db.Integer, default=0)
    womens_singles_points = db.Column(db.Integer, default=0)
    mens_doubles_points = db.Column(db.Integer, default=0)
    womens_doubles_points = db.Column(db.Integer, default=0)
    mixed_doubles_points = db.Column(db.Integer, default=0)
    
    # Relationships
    registrations = db.relationship('Registration', 
                                    backref='player', 
                                    lazy='dynamic',
                                    foreign_keys='Registration.player_id')

    partner_registrations = db.relationship('Registration',
                                            backref='partner',
                                            lazy='dynamic',
                                            foreign_keys='Registration.partner_id')
    
    def get_points(self, category_type):
        if category_type == CategoryType.MENS_SINGLES:
            return self.mens_singles_points
        elif category_type == CategoryType.WOMENS_SINGLES:
            return self.womens_singles_points
        elif category_type == CategoryType.MENS_DOUBLES:
            return self.mens_doubles_points
        elif category_type == CategoryType.WOMENS_DOUBLES:
            return self.womens_doubles_points
        elif category_type == CategoryType.MIXED_DOUBLES:
            return self.mixed_doubles_points
        return 0

class Tournament(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    organizer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    location = db.Column(db.String(200))
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

    # Door gifts (prize fields already exist in your model)
    door_gifts = db.Column(db.Text, nullable=True)
    door_gifts_image = db.Column(db.String(255), nullable=True)
    
    # Relationships
    categories = db.relationship('TournamentCategory', backref='tournament', lazy='dynamic')

    def is_completed(self):
        return self.status == TournamentStatus.COMPLETED

    @property
    def prize_summary(self):
        """Get overall prize summary statistics"""
        return {
            'total_cash': self.total_cash_prize,
            'total_value': self.total_prize_value,
            'merchandise_value': self.total_prize_value - self.total_cash_prize,
            'category_count': self.categories.count(),
            'has_merchandise': any(cat.has_merchandise for cat in self.categories),
            'has_trophies': any(cat.has_trophies for cat in self.categories)
        }

    @property
    def winners_by_category(self):
        """Return a dictionary of winners for each category in this tournament."""
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
                    if final_match.winning_team:
                        # For doubles, we return a list of two players
                        category_results[1] = [
                            final_match.winning_team.player1,
                            final_match.winning_team.player2
                        ]
                else:
                    if final_match.winning_player:
                        category_results[1] = final_match.winning_player
                
                # Get runners-up (2nd place)
                if is_doubles:
                    if final_match.losing_team:
                        category_results[2] = [
                            final_match.losing_team.player1,
                            final_match.losing_team.player2
                        ]
                else:
                    if final_match.losing_player:
                        category_results[2] = final_match.losing_player
                
                # Handle semifinalists (3rd/4th place)
                # ... similar logic as above, adapted for doubles teams
            
            # Only add categories that have winners
            if category_results:
                result[category.category_type.value] = category_results
        
        return result
    
    def is_registration_open(self):
        return datetime.utcnow() < self.registration_deadline

# Enhancement for TournamentCategory to support restrictions
class TournamentCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'))
    category_type = db.Column(Enum(CategoryType))
    name = db.Column(db.String(100)) 
    max_participants = db.Column(db.Integer)
    points_awarded = db.Column(db.Integer)
    format = db.Column(Enum(TournamentFormat), default=TournamentFormat.SINGLE_ELIMINATION)
    registration_fee = db.Column(db.Float, default=0.0)
    description = db.Column(db.Text)

    # display order field (lower number = higher priority)
    display_order = db.Column(db.Integer, default=999)
    
    # Prize money details
    prize_percentage = db.Column(db.Float, default=0)  # Percentage of total prize pool
    prize_money = db.Column(db.Float, default=0.0)  # Total cash prize for this category
    prize_image = db.Column(db.String(255), nullable=True)
    
    has_merchandise = db.Column(db.Boolean, default=False)  # Quick flag for filtering
    has_trophies = db.Column(db.Boolean, default=False)  # Quick flag for filtering
    prize_summary = db.Column(db.Text, nullable=True)  # Brief overview for display

    total_prize_value = db.Column(db.Float, default=0.0)

    # New category restrictions
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
    # Structure: {"1": 100, "2": 70, "3-4": 50, "5-8": 25, etc.}
    points_distribution = db.Column(JSON, default={})
    
    # Custom prize distribution as JSON
    # Structure: {"1": 50, "2": 25, "3-4": 12.5, "5-8": 6.25, etc.}
    prize_distribution = db.Column(JSON, default={})
    
    # Relationships
    registrations = db.relationship('Registration', backref='category', lazy='dynamic')
    matches = db.relationship('Match', backref='category', lazy='dynamic')
    groups = db.relationship('Group', backref='category', lazy='dynamic')

    def is_doubles(self):
        return self.category_type in [
            CategoryType.MENS_DOUBLES, 
            CategoryType.WOMENS_DOUBLES, 
            CategoryType.MIXED_DOUBLES
        ]
    
    def calculate_prize_money(self, total_prize_pool):
        """Calculate actual prize money based on percentage of total pool"""
        self.prize_money = total_prize_pool * (self.prize_percentage / 100)
        return self.prize_money
    
    def get_points_for_place(self, place):
        """Get points for a specific place based on distribution"""
        if not self.points_distribution:
            # Default distribution if none set
            return self._default_points_for_place(place)
        
        # Find the matching place in the distribution
        for place_range, percentage in self.points_distribution.items():
            if self._is_in_place_range(place, place_range):
                return int(self.points_awarded * (percentage / 100))
        
        return 0
    
    def get_prize_for_place(self, place):
        """Get prize money for a specific place based on distribution"""
        if not self.prize_distribution:
            # Default distribution if none set
            return self._default_prize_for_place(place)
        
        # Find the matching place in the distribution
        for place_range, percentage in self.prize_distribution.items():
            if self._is_in_place_range(place, place_range):
                return self.prize_money * (percentage / 100)
        
        return 0
    
    def calculate_prize_values(self):
        """Calculate and update prize values based on tournament prize pool"""
        if not self.tournament or not self.tournament.prize_pool:
            return
            
        # Calculate cash prize based on percentage
        if self.prize_percentage > 0:
            self.prize_money = self.tournament.prize_pool * (self.prize_percentage / 100)
        
        # Create default cash prizes if none exist but there's prize money
        if self.prize_money > 0 and not self.prizes.filter_by(prize_type=PrizeType.CASH).count():
            if self.prize_distribution:
                # Create prizes based on distribution
                for placement, percentage in self.prize_distribution.items():
                    amount = self.prize_money * (percentage / 100)
                    prize = Prize(
                        category_id=self.id,
                        placement=placement,
                        prize_type=PrizeType.CASH,
                        cash_amount=amount
                    )
                    db.session.add(prize)
        
        # Update total value
        total = self.prize_money  # Start with cash
        for prize in self.prizes:
            if prize.prize_type != PrizeType.CASH:
                total += prize.monetary_value * prize.quantity
        
        self.total_prize_value = total
        
        # Update flags
        self.has_merchandise = self.prizes.filter(Prize.prize_type.in_([
            PrizeType.MERCHANDISE, PrizeType.VOUCHER, PrizeType.SPONSORED_PRODUCT
        ])).count() > 0
        
        self.has_trophies = self.prizes.filter_by(prize_type=PrizeType.TROPHY).count() > 0
        
        # Update tournament totals
        self.tournament.total_cash_prize = sum(cat.prize_money for cat in self.tournament.categories)
        self.tournament.total_prize_value = sum(cat.total_prize_value for cat in self.tournament.categories)

    def add_merchandise_prize(self, placement, title, value, description=None, image=None, quantity=1):
        """Add a merchandise prize to this category"""
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
        self.has_merchandise = True
        return prize

    def add_trophy(self, placement, title="Trophy", description=None, image=None):
        """Add a trophy to this category"""
        prize = Prize(
            category_id=self.id,
            placement=placement,
            prize_type=PrizeType.TROPHY,
            title=title,
            description=description,
            image=image,
            monetary_value=0.0  # Typically not counted in monetary value
        )
        db.session.add(prize)
        self.has_trophies = True
        return prize

    def _is_in_place_range(self, place, place_range):
        """Check if a place is within a range like '1', '2', '3-4', '5-8', etc."""
        if '-' in place_range:
            start, end = map(int, place_range.split('-'))
            return start <= place <= end
        else:
            return place == int(place_range)
    
    def _default_points_for_place(self, place):
        """Default points distribution if none specified"""
        if place == 1:
            return self.points_awarded
        elif place == 2:
            return int(self.points_awarded * 0.7)
        elif place <= 4:
            return int(self.points_awarded * 0.5)
        elif place <= 8:
            return int(self.points_awarded * 0.25)
        elif place <= 16:
            return int(self.points_awarded * 0.15)
        return 0
    
    def _default_prize_for_place(self, place):
        """Default prize distribution if none specified"""
        if place == 1:
            return self.prize_money * 0.5
        elif place == 2:
            return self.prize_money * 0.25
        elif place <= 4:
            return self.prize_money * 0.125
        elif place <= 8:
            return self.prize_money * 0.0625
        return 0

    @property
    def grouped_prizes(self):
        """Group prizes by placement for easy display"""
        result = {}
        for prize in self.prizes:
            if prize.placement not in result:
                result[prize.placement] = []
            result[prize.placement].append(prize)
        return result

class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player_profile.id'))
    category_id = db.Column(db.Integer, db.ForeignKey('tournament_category.id'))
    partner_id = db.Column(db.Integer, db.ForeignKey('player_profile.id'), nullable=True)  # For doubles
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_approved = db.Column(db.Boolean, default=False)
    seed = db.Column(db.Integer, nullable=True)  # For tournament seeding
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('refunded', 'Refunded')
    ]
    payment_status = db.Column(db.String(20), default='pending')
    payment_date = db.Column(db.DateTime, nullable=True)
    payment_reference = db.Column(db.String(100), nullable=True)

    # Add payment proof fields
    payment_proof = db.Column(db.String(255), nullable=True)
    payment_proof_uploaded_at = db.Column(db.DateTime, nullable=True)
    payment_notes = db.Column(db.Text, nullable=True)

    # Add payment verification
    payment_verified = db.Column(db.Boolean, default=False)
    payment_verified_at = db.Column(db.DateTime, nullable=True)
    payment_verified_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    payment_rejection_reason = db.Column(db.Text, nullable=True)


    def create_team(self, partner_registration):
        """Create a team from this registration and a partner registration"""
        if not partner_registration:
            return None
            
        team = Team(
            player1_id=self.player_id,
            player2_id=partner_registration.player_id,
            category_id=self.category_id
        )
        db.session.add(team)
        return team


class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player1_id = db.Column(db.Integer, db.ForeignKey('player_profile.id'), nullable=False)
    player2_id = db.Column(db.Integer, db.ForeignKey('player_profile.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('tournament_category.id'))
    
    # Relationships
    player1 = db.relationship('PlayerProfile', foreign_keys=[player1_id])
    player2 = db.relationship('PlayerProfile', foreign_keys=[player2_id])
    category = db.relationship('TournamentCategory', backref='teams')
    
# New model for group stage
class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('tournament_category.id'))
    name = db.Column(db.String(50))  # e.g., "Group A"
    
    # Relationships
    standings = db.relationship('GroupStanding', backref='group', lazy='dynamic')
    matches = db.relationship('Match', backref='group', lazy='dynamic')

# New model for group stage standings
class GroupStanding(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    
    # Can link to either player or team
    player_id = db.Column(db.Integer, db.ForeignKey('player_profile.id'), nullable=True)
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    
    # Stats
    matches_played = db.Column(db.Integer, default=0)
    matches_won = db.Column(db.Integer, default=0)
    matches_lost = db.Column(db.Integer, default=0)
    sets_won = db.Column(db.Integer, default=0)
    sets_lost = db.Column(db.Integer, default=0)
    points_won = db.Column(db.Integer, default=0)
    points_lost = db.Column(db.Integer, default=0)
    
    # Calculated position in group
    position = db.Column(db.Integer, nullable=True)
    
    # Relationships
    player = db.relationship('PlayerProfile', backref='group_standings')
    team = db.relationship('Team', backref='group_standings')

class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('tournament_category.id'))
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=True)
    
    # Dynamic properties for tracking match stage and round
    stage = db.Column(Enum(MatchStage), default=MatchStage.KNOCKOUT)
    round = db.Column(db.Integer)  # 1=final, 2=semifinal, etc. or group stage round number
    match_order = db.Column(db.Integer)  # Order within the round/group
    
    # Scheduling info
    court = db.Column(db.String(50), nullable=True)
    scheduled_time = db.Column(db.DateTime, nullable=True)
    
    # For singles matches
    player1_id = db.Column(db.Integer, db.ForeignKey('player_profile.id'), nullable=True)
    player2_id = db.Column(db.Integer, db.ForeignKey('player_profile.id'), nullable=True)
    
    # For doubles matches
    team1_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    team2_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    
    # Winners can be either individual players (singles) or teams (doubles)
    winning_player_id = db.Column(db.Integer, db.ForeignKey('player_profile.id'), nullable=True)
    winning_team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    
    # Losers can be either individual players (singles) or teams (doubles)
    losing_player_id = db.Column(db.Integer, db.ForeignKey('player_profile.id'), nullable=True)
    losing_team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    
    completed = db.Column(db.Boolean, default=False)
    next_match_id = db.Column(db.Integer, db.ForeignKey('match.id'), nullable=True)
    
    # Existing relationships
    scores = db.relationship('MatchScore', backref='match', lazy='dynamic')
    player1 = db.relationship('PlayerProfile', foreign_keys=[player1_id])
    player2 = db.relationship('PlayerProfile', foreign_keys=[player2_id])
    team1 = db.relationship('Team', foreign_keys=[team1_id])
    team2 = db.relationship('Team', foreign_keys=[team2_id])
    winning_player = db.relationship('PlayerProfile', foreign_keys=[winning_player_id])
    winning_team = db.relationship('Team', foreign_keys=[winning_team_id])
    losing_player = db.relationship('PlayerProfile', foreign_keys=[losing_player_id])
    losing_team = db.relationship('Team', foreign_keys=[losing_team_id])
    next_match = db.relationship('Match', remote_side=[id], backref='previous_matches')

    @property
    def is_doubles(self):
        """Check if this is a doubles match based on category type"""
        if not self.category:
            return False
        return self.category.is_doubles()
    
    @property
    def round_name(self):
        """Get human-readable round name based on round number"""
        if self.stage == MatchStage.GROUP:
            return f"Group {self.group.name if self.group else ''} Round"
            
        if self.round == 1:
            return "Final"
        elif self.round == 2:
            return "Semifinal"
        elif self.round == 3:
            return "Quarterfinal"
        elif self.round == 4:
            return "Round of 16"
        elif self.round == 5:
            return "Round of 32"
        elif self.round == 6:
            return "Round of 64"
        else:
            return f"Round {self.round}"
    
    @property
    def winner_id(self):
        """Get the ID of the winner (player or team)"""
        if self.is_doubles:
            return self.winning_team_id
        return self.winning_player_id
    
    @property
    def loser_id(self):
        """Get the ID of the loser (player or team)"""
        if self.is_doubles:
            return self.losing_team_id
        return self.losing_player_id
    
    @property 
    def winner(self):
        """Get the winner (player or team)"""
        if self.is_doubles:
            return self.winning_team
        return self.winning_player
    
    @property
    def loser(self):
        """Get the loser (player or team)"""
        if self.is_doubles:
            return self.losing_team
        return self.losing_player


class MatchScore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('match.id'))
    set_number = db.Column(db.Integer)
    player1_score = db.Column(db.Integer, default=0)
    player2_score = db.Column(db.Integer, default=0)
    

class Equipment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player_profile.id'))
    brand = db.Column(db.String(100))
    name = db.Column(db.String(200))
    image = db.Column(db.String(255))
    buy_link = db.Column(db.String(255))
    
    player = db.relationship('PlayerProfile', backref=db.backref('equipment', lazy='dynamic'))
    
class PlayerSponsor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player_profile.id'))
    name = db.Column(db.String(100))
    logo = db.Column(db.String(255))
    link = db.Column(db.String(255))
    
    player = db.relationship('PlayerProfile', backref=db.backref('player_sponsors', lazy='dynamic'))
    
class PlatformSponsor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    logo = db.Column(db.String(255))
    website = db.Column(db.String(255))
    is_featured = db.Column(db.Boolean, default=False)
    tier = db.Column(db.String(50))  # 'Premier', 'Official', 'Featured', etc.
    description = db.Column(db.Text)
    
    # Relationships
    tournaments = db.relationship('Tournament', secondary='tournament_sponsors', backref='platform_sponsors')

# Association table for tournament sponsors
tournament_sponsors = db.Table('tournament_sponsors',
    db.Column('tournament_id', db.Integer, db.ForeignKey('tournament.id'), primary_key=True),
    db.Column('sponsor_id', db.Integer, db.ForeignKey('platform_sponsor.id'), primary_key=True)
)

class Venue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(255))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    country = db.Column(db.String(100))
    description = db.Column(db.Text)
    image = db.Column(db.String(255))
    website = db.Column(db.String(255))
    postal_code = db.Column(db.String(20))
    is_featured = db.Column(db.Boolean, default=False)
    court_count = db.Column(db.Integer, default=0)
    
    # Relationship with tournaments
    tournaments = db.relationship('Tournament', backref='venue', lazy='dynamic')

class Advertisement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    image = db.Column(db.String(255), nullable=False)
    link = db.Column(db.String(255))
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime)
    position = db.Column(db.String(50))  # 'hero', 'sidebar', 'footer', etc.
    is_active = db.Column(db.Boolean, default=True)
    views = db.Column(db.Integer, default=0)
    clicks = db.Column(db.Integer, default=0)
    
class PrizeType(enum.Enum):
    CASH = "cash"
    MERCHANDISE = "merchandise" 
    VOUCHER = "voucher"
    TROPHY = "trophy"
    MEDAL = "medal"
    SPONSORED_PRODUCT = "sponsored_product"

class Prize(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('tournament_category.id'))
    placement = db.Column(db.String(20))  # "1", "2", "3-4", etc.
    prize_type = db.Column(Enum(PrizeType), default=PrizeType.CASH)
    
    # For cash prizes
    cash_amount = db.Column(db.Float, default=0.0)
    
    # For non-cash prizes
    title = db.Column(db.String(100))  # "Pro Paddle", "Nike Shoes", etc.
    description = db.Column(db.Text, nullable=True)
    image = db.Column(db.String(255), nullable=True)
    monetary_value = db.Column(db.Float, default=0.0)  # Estimated value
    quantity = db.Column(db.Integer, default=1)
    
    # For vouchers/gift cards
    vendor = db.Column(db.String(100), nullable=True)
    expiry_date = db.Column(db.DateTime, nullable=True)
    
    # For sponsored products
    sponsor_id = db.Column(db.Integer, db.ForeignKey('platform_sponsor.id'), nullable=True)
    
    # Relationships
    category = db.relationship('TournamentCategory', backref='prizes')
    sponsor = db.relationship('PlatformSponsor', backref='sponsored_prizes')

class TeamRegistration(db.Model):
    """Model for team registrations without requiring accounts"""
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'))
    category_id = db.Column(db.Integer, db.ForeignKey('tournament_category.id'))
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Payment info
    registration_fee = db.Column(db.Float, default=0.0)
    payment_status = db.Column(db.String(20), default='pending')  # pending, paid, refunded
    payment_date = db.Column(db.DateTime, nullable=True)
    payment_reference = db.Column(db.String(100), nullable=True)
    payment_proof = db.Column(db.String(255), nullable=True)
    
    # Additional details
    special_requests = db.Column(db.Text, nullable=True)
    
    # Agreements
    terms_agreement = db.Column(db.Boolean, default=False)
    liability_waiver = db.Column(db.Boolean, default=False)
    media_release = db.Column(db.Boolean, default=False)
    pdpa_consent = db.Column(db.Boolean, default=False)
    
    # Player 1 details
    player1_name = db.Column(db.String(100), nullable=False)
    player1_email = db.Column(db.String(120), nullable=False)
    player1_phone = db.Column(db.String(20), nullable=False)
    player1_dupr_id = db.Column(db.String(50), nullable=False)
    player1_dupr_rating = db.Column(db.Float, nullable=True)  # Retrieved from API
    player1_date_of_birth = db.Column(db.Date, nullable=False)
    player1_nationality = db.Column(db.String(50), nullable=False)
    player1_account_created = db.Column(db.Boolean, default=False)
    player1_temp_password = db.Column(db.String(20), nullable=True)
    
    # Player 2 details
    player2_name = db.Column(db.String(100), nullable=False)
    player2_email = db.Column(db.String(120), nullable=False)
    player2_phone = db.Column(db.String(20), nullable=False)
    player2_dupr_id = db.Column(db.String(50), nullable=False)
    player2_dupr_rating = db.Column(db.Float, nullable=True)  # Retrieved from API
    player2_date_of_birth = db.Column(db.Date, nullable=False)
    player2_nationality = db.Column(db.String(50), nullable=False)
    player2_account_created = db.Column(db.Boolean, default=False)
    player2_temp_password = db.Column(db.String(20), nullable=True)
    
    # Admin fields
    admin_notes = db.Column(db.Text, nullable=True)
    is_approved = db.Column(db.Boolean, default=False)
    
    # Relationships
    tournament = db.relationship('Tournament', backref=db.backref('team_registrations', lazy='dynamic'))
    category = db.relationship('TournamentCategory', backref=db.backref('team_registrations', lazy='dynamic'))
    
    def __repr__(self):
        return f'<TeamRegistration {self.player1_name}/{self.player2_name} - {self.category.name}>'
    
    @property
    def team_name(self):
        return f"{self.player1_name} / {self.player2_name}"
    
    @property
    def team_dupr(self):
        """Calculate average DUPR rating for the team"""
        if self.player1_dupr_rating and self.player2_dupr_rating:
            return (self.player1_dupr_rating + self.player2_dupr_rating) / 2
        return None
    
    @property
    def is_eligible(self):
        """Check if team is eligible for the selected category based on DUPR rating"""
        if not self.category or not self.category.max_dupr_rating:
            return True
            
        if not self.player1_dupr_rating or not self.player2_dupr_rating:
            return True  # Can't determine without ratings
            
        return (self.player1_dupr_rating <= self.category.max_dupr_rating and 
                self.player2_dupr_rating <= self.category.max_dupr_rating)
                
    def fetch_dupr_ratings(self):
        """Fetch DUPR ratings from API based on DUPR IDs"""
        # This would be implemented to call the DUPR API
        # For now, we'll use a placeholder function
        self.player1_dupr_rating = self._fetch_dupr_rating(self.player1_dupr_id)
        self.player2_dupr_rating = self._fetch_dupr_rating(self.player2_dupr_id)
        
    def _fetch_dupr_rating(self, dupr_id):
        """Call DUPR API to get rating from ID
        This is a placeholder that would need to be implemented with actual API calls
        """
        # TODO: Implement actual API call to DUPR
        import requests
        
        # Example API endpoint (replace with actual DUPR API endpoint)
        url = f"https://api.mydupr.com/players/{dupr_id}/rating"
        
        try:
            # Make API request (would need proper authentication)
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                return data.get('rating')
        except Exception as e:
            current_app.logger.error(f"Error fetching DUPR rating: {e}")
        
        return None  # Return None if rating couldn't be fetched
        
    def create_user_accounts(self):
        """Create user accounts for both players with temporary passwords"""
        from app.models import User
        from app.helpers.registration import generate_temp_password
        
        # Check if accounts already exist
        user1 = User.query.filter_by(email=self.player1_email).first()
        user2 = User.query.filter_by(email=self.player2_email).first()
        
        # Create account for player 1 if needed
        if not user1:
            self.player1_temp_password = generate_temp_password()
            print(self.player1_email)
            print(self.player1_temp_password)
            user1 = User(
                username=self.player1_email,  # Use part before @ as username
                email=self.player1_email,
                full_name=self.player1_name,
                role=UserRole.PLAYER
            )
            user1.set_password(self.player1_temp_password)
            db.session.add(user1)
            self.player1_account_created = True
            
        # Create account for player 2 if needed
        if not user2:
            self.player2_temp_password = generate_temp_password()
            print(self.player2_email)
            print(self.player2_temp_password)
            user2 = User(
                username=self.player2_email,  # Use part before @ as username
                email=self.player2_email, 
                full_name=self.player2_name,
                role=UserRole.PLAYER
            )
            user2.set_password(self.player2_temp_password)
            db.session.add(user2)
            self.player2_account_created = True
            
        db.session.commit()
        
    def send_confirmation_emails(self):
        """Send confirmation emails to both players"""
        from app.helpers.email_utils import send_email
        
        # Send email to player 1
        subject = f"Registration Confirmation - {self.tournament.name}"
        if self.player1_account_created:
            body = f"""
            Dear {self.player1_name},
            
            Thank you for registering for {self.tournament.name}. Your registration has been received.
            
            Registration Details:
            - Team: {self.team_name}
            - Category: {self.category.name}
            - Registration Fee: RM{self.registration_fee:.2f}
            - Payment Status: {self.payment_status.capitalize()}
            
            Your temporary account has been created:
            - Email: {self.player1_email}
            - Temporary Password: {self.player1_temp_password}
            
            Please login to your account and change your password as soon as possible.
            
            If you have any questions, please contact us.
            
            Best regards,
            The Tournament Team
            """
        else:
            body = f"""
            Dear {self.player1_name},
            
            Thank you for registering for {self.tournament.name}. Your registration has been received.
            
            Registration Details:
            - Team: {self.team_name}
            - Category: {self.category.name}
            - Registration Fee: RM{self.registration_fee:.2f}
            - Payment Status: {self.payment_status.capitalize()}
            
            If you have any questions, please contact us.
            
            Best regards,
            The Tournament Team
            """
            
        send_email(subject, body, [self.player1_email])
        
        # Send email to player 2
        if self.player2_account_created:
            body = f"""
            Dear {self.player2_name},
            
            Thank you for registering for {self.tournament.name}. Your registration has been received.
            
            Registration Details:
            - Team: {self.team_name}
            - Category: {self.category.name}
            - Registration Fee: RM{self.registration_fee:.2f}
            - Payment Status: {self.payment_status.capitalize()}
            
            Your temporary account has been created:
            - Email: {self.player2_email}
            - Temporary Password: {self.player2_temp_password}
            
            Please login to your account and change your password as soon as possible.
            
            If you have any questions, please contact us.
            
            Best regards,
            The Tournament Team
            """
        else:
            body = f"""
            Dear {self.player2_name},
            
            Thank you for registering for {self.tournament.name}. Your registration has been received.
            
            Registration Details:
            - Team: {self.team_name}
            - Category: {self.category.name}
            - Registration Fee: RM{self.registration_fee:.2f}
            - Payment Status: {self.payment_status.capitalize()}
            
            If you have any questions, please contact us.
            
            Best regards,
            The Tournament Team
            """
            
        send_email(subject, body, [self.player2_email])
