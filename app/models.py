from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login
import enum
from sqlalchemy import Enum, Table, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

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

# Association table for player partnerships (for doubles)
partnerships = db.Table('partnerships',
    db.Column('partnership_id', db.Integer, primary_key=True),
    db.Column('player1_id', db.Integer, db.ForeignKey('player_profile.id')),
    db.Column('player2_id', db.Integer, db.ForeignKey('player_profile.id')),
    db.Column('category_id', db.Integer, db.ForeignKey('tournament_category.id'))
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(Enum(UserRole), default=UserRole.PLAYER)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    player_profile = db.relationship('PlayerProfile', backref='user', uselist=False, lazy='dynamic')
    tournaments_organized = db.relationship('Tournament', backref='organizer', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
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
    registrations = db.relationship('Registration', backref='player', lazy='dynamic')
    
    def __repr__(self):
        return f'<PlayerProfile {self.full_name}>'
    
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
    
    # Relationships
    categories = db.relationship('TournamentCategory', backref='tournament', lazy='dynamic')
    
    def __repr__(self):
        return f'<Tournament {self.name}>'
    
    def is_registration_open(self):
        return datetime.utcnow() < self.registration_deadline

class TournamentCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'))
    category_type = db.Column(Enum(CategoryType))
    max_participants = db.Column(db.Integer)
    points_awarded = db.Column(db.Integer)
    
    # Relationships
    registrations = db.relationship('Registration', backref='category', lazy='dynamic')
    matches = db.relationship('Match', backref='category', lazy='dynamic')
    
    def __repr__(self):
        return f'<TournamentCategory {self.category_type.value} for Tournament {self.tournament_id}>'

class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player_profile.id'))
    category_id = db.Column(db.Integer, db.ForeignKey('tournament_category.id'))
    partner_id = db.Column(db.Integer, db.ForeignKey('player_profile.id'), nullable=True)  # For doubles
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_approved = db.Column(db.Boolean, default=False)
    seed = db.Column(db.Integer, nullable=True)  # For tournament seeding
    
    def __repr__(self):
        return f'<Registration {self.player_id} for Category {self.category_id}>'

class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('tournament_category.id'))
    round = db.Column(db.Integer)  # Round number in the tournament
    court = db.Column(db.String(50), nullable=True)
    scheduled_time = db.Column(db.DateTime, nullable=True)
    player1_id = db.Column(db.Integer, db.ForeignKey('player_profile.id'), nullable=True)
    player2_id = db.Column(db.Integer, db.ForeignKey('player_profile.id'), nullable=True)
    player1_partner_id = db.Column(db.Integer, db.ForeignKey('player_profile.id'), nullable=True)  # For doubles
    player2_partner_id = db.Column(db.Integer, db.ForeignKey('player_profile.id'), nullable=True)  # For doubles
    winner_id = db.Column(db.Integer, db.ForeignKey('player_profile.id'), nullable=True)
    loser_id = db.Column(db.Integer, db.ForeignKey('player_profile.id'), nullable=True)
    completed = db.Column(db.Boolean, default=False)
    match_order = db.Column(db.Integer)  # Order within the round (for bracket placement)
    next_match_id = db.Column(db.Integer, db.ForeignKey('match.id'), nullable=True)
    
    # Relationships
    scores = db.relationship('MatchScore', backref='match', lazy='dynamic')
    player1 = db.relationship('PlayerProfile', foreign_keys=[player1_id])
    player2 = db.relationship('PlayerProfile', foreign_keys=[player2_id])
    player1_partner = db.relationship('PlayerProfile', foreign_keys=[player1_partner_id])
    player2_partner = db.relationship('PlayerProfile', foreign_keys=[player2_partner_id])
    winner = db.relationship('PlayerProfile', foreign_keys=[winner_id])
    loser = db.relationship('PlayerProfile', foreign_keys=[loser_id])
    next_match = db.relationship('Match', remote_side=[id], backref='previous_matches')
    
    def __repr__(self):
        return f'<Match {self.id} in Round {self.round}>'

class MatchScore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('match.id'))
    set_number = db.Column(db.Integer)
    player1_score = db.Column(db.Integer, default=0)
    player2_score = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<MatchScore for Match {self.match_id}, Set {self.set_number}>'

class Equipment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player_profile.id'))
    brand = db.Column(db.String(100))
    name = db.Column(db.String(200))
    image = db.Column(db.String(255))
    buy_link = db.Column(db.String(255))
    
    player = db.relationship('PlayerProfile', backref=db.backref('equipment', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Equipment {self.name} for Player {self.player_id}>'

class Sponsor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player_profile.id'))
    name = db.Column(db.String(100))
    logo = db.Column(db.String(255))
    link = db.Column(db.String(255))
    
    player = db.relationship('PlayerProfile', backref=db.backref('sponsors', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Sponsor {self.name} for Player {self.player_id}>'
