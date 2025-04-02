from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Enum, Column, Integer, String, Boolean, DateTime, ForeignKey, Date, Text, JSON
from sqlalchemy.orm import relationship
from app import db, login
from app.models.enums import UserRole, CategoryType # Import necessary enums

class User(UserMixin, db.Model):
    __tablename__ = 'user' # Explicitly define table name if needed, though Flask-SQLAlchemy usually infers it
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100))
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    ic_number = db.Column(db.String(50), unique=True, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    password_hash = db.Column(db.String(128))
    role = db.Column(Enum(UserRole), default=UserRole.PLAYER)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Added for digital signature verification (for match results)
    digital_signature_hash = db.Column(db.String(128), nullable=True)

    # Relationships
    # Use string for relationship target to avoid circular imports initially
    player_profile = db.relationship('PlayerProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    tournaments_organized = db.relationship('Tournament', backref='organizer', lazy='dynamic')
    submitted_tickets = db.relationship('SupportTicket', foreign_keys='SupportTicket.submitter_id', backref='submitter', lazy='dynamic')
    ticket_responses = db.relationship('TicketResponse', backref='user', lazy='dynamic')
    payment_verifications = db.relationship('Registration', foreign_keys='Registration.payment_verified_by', backref='verifier', lazy='dynamic')


    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def set_digital_signature(self, signature):
        """Set a digital signature for the user (for match result verification)"""
        self.digital_signature_hash = generate_password_hash(signature)
        
    def verify_digital_signature(self, signature):
        """Verify a digital signature"""
        if not self.digital_signature_hash:
            return False
        return check_password_hash(self.digital_signature_hash, signature)

    def is_admin(self):
        return self.role == UserRole.ADMIN

    def is_organizer(self):
        return self.role == UserRole.ORGANIZER or self.role == UserRole.ADMIN
        
    def is_referee(self):
        return self.role == UserRole.REFEREE

    def is_player(self):
        return self.role == UserRole.PLAYER

    def __repr__(self):
        return f'<User {self.username}>'

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class PlayerProfile(db.Model):
    __tablename__ = 'player_profile'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    dupr_id = db.Column(db.String(50), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    full_name = db.Column(db.String(100))
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
    
    # New fields added for social media
    instagram = db.Column(db.String(255))
    facebook = db.Column(db.String(255))
    twitter = db.Column(db.String(255))
    tiktok = db.Column(db.String(255))  # Added as required
    xiaohongshu = db.Column(db.String(255))  # Added as required
    
    # Coach/academy affiliation (required by Phase 3)
    coach_academy = db.Column(db.String(255))
    
    # Detailed statistics (using Text field instead of JSON for better compatibility)
    stats = db.Column(db.Text, default='{}')
    
    # Basic stats counters (could be calculated from matches if needed)
    matches_won = db.Column(db.Integer, default=0)
    matches_lost = db.Column(db.Integer, default=0)
    avg_match_duration = db.Column(db.Integer, default=0)  # in minutes
    
    turned_pro = db.Column(db.Integer)

    # Rankings
    mens_singles_points = db.Column(db.Integer, default=0)
    womens_singles_points = db.Column(db.Integer, default=0)
    mens_doubles_points = db.Column(db.Integer, default=0)
    womens_doubles_points = db.Column(db.Integer, default=0)
    mixed_doubles_points = db.Column(db.Integer, default=0)

    # Relationships
    # Use strings for relationship targets
    registrations = db.relationship('Registration',
                                    backref='player',
                                    lazy='dynamic',
                                    foreign_keys='Registration.player_id')

    partner_registrations = db.relationship('Registration',
                                            backref='partner',
                                            lazy='dynamic',
                                            foreign_keys='Registration.partner_id')

    equipment = db.relationship('Equipment', backref='player', lazy='dynamic', cascade='all, delete-orphan')
    player_sponsors = db.relationship('PlayerSponsor', backref='player', lazy='dynamic', cascade='all, delete-orphan')
    group_standings = db.relationship('GroupStanding', backref='player', lazy='dynamic')
    player_reports = db.relationship('SupportTicket', backref='reported_player', lazy='dynamic')

    # Matches (Singles)
    matches_as_player1 = db.relationship('Match', foreign_keys='Match.player1_id', backref='player1_profile', lazy='dynamic')
    matches_as_player2 = db.relationship('Match', foreign_keys='Match.player2_id', backref='player2_profile', lazy='dynamic')
    matches_won_singles = db.relationship('Match', foreign_keys='Match.winning_player_id', backref='winning_player_profile', lazy='dynamic')
    matches_lost_singles = db.relationship('Match', foreign_keys='Match.losing_player_id', backref='losing_player_profile', lazy='dynamic')

    # Matches (Doubles - via Team)
    # Access through Team model relationships

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
        
    def update_match_stats(self):
        """Update match statistics"""
        # Count singles matches won and lost
        singles_won = self.matches_won_singles.count()
        singles_lost = self.matches_lost_singles.count()
        
        # Count doubles matches won and lost through teams
        doubles_won = 0
        doubles_lost = 0
        
        # Teams where this player is player1
        teams_as_player1 = db.session.query('Team').filter_by(player1_id=self.id).all()
        # Teams where this player is player2
        teams_as_player2 = db.session.query('Team').filter_by(player2_id=self.id).all()
        
        for team in teams_as_player1 + teams_as_player2:
            doubles_won += team.matches_won.count()
            doubles_lost += team.matches_lost.count()
            
        # Update stats
        self.matches_won = singles_won + doubles_won
        self.matches_lost = singles_lost + doubles_lost
        
        # We could calculate avg_match_duration here if we had match duration data
        
        return {
            'singles_won': singles_won,
            'singles_lost': singles_lost,
            'doubles_won': doubles_won,
            'doubles_lost': doubles_lost,
            'total_won': self.matches_won,
            'total_lost': self.matches_lost
        }

    def __repr__(self):
        return f'<PlayerProfile {self.full_name}>'