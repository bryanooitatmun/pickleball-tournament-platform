from datetime import datetime
from sqlalchemy import Enum, Column, Integer, ForeignKey, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from app import db
from app.models.enums import MatchStage, CategoryType # Import necessary enums

class Team(db.Model):
    __tablename__ = 'team'
    id = db.Column(db.Integer, primary_key=True)
    player1_id = db.Column(db.Integer, db.ForeignKey('player_profile.id'), nullable=False)
    player2_id = db.Column(db.Integer, db.ForeignKey('player_profile.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('tournament_category.id')) # Link team to a specific category instance

    # Relationships (use strings)
    player1 = db.relationship('PlayerProfile', foreign_keys=[player1_id])
    player2 = db.relationship('PlayerProfile', foreign_keys=[player2_id])
    category = db.relationship('TournamentCategory', backref='teams')

    # Matches as Team 1
    matches_as_team1 = db.relationship('Match', foreign_keys='Match.team1_id', backref='team1_profile', lazy='dynamic')
    # Matches as Team 2
    matches_as_team2 = db.relationship('Match', foreign_keys='Match.team2_id', backref='team2_profile', lazy='dynamic')
    # Matches won
    matches_won = db.relationship('Match', foreign_keys='Match.winning_team_id', backref='winning_team_profile', lazy='dynamic')
    # Matches lost
    matches_lost = db.relationship('Match', foreign_keys='Match.losing_team_id', backref='losing_team_profile', lazy='dynamic')

    group_standings = db.relationship('GroupStanding', backref='team', lazy='dynamic')

    def __repr__(self):
        p1_name = self.player1.full_name if self.player1 else 'N/A'
        p2_name = self.player2.full_name if self.player2 else 'N/A'
        return f'<Team {self.id}: {p1_name} / {p2_name}>'

class Group(db.Model):
    __tablename__ = 'group'
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('tournament_category.id'))
    name = db.Column(db.String(50))  # e.g., "Group A"

    # Relationships (use strings)
    standings = db.relationship('GroupStanding', backref='group', lazy='dynamic', cascade='all, delete-orphan')
    matches = db.relationship('Match', backref='group', lazy='dynamic')
    # category relationship defined in TournamentCategory model via backref

    def __repr__(self):
        return f'<Group {self.name}>'

class GroupStanding(db.Model):
    __tablename__ = 'group_standing'
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

    # Relationships (use strings)
    # group relationship defined in Group model via backref
    # player relationship defined in PlayerProfile model via backref
    # team relationship defined in Team model via backref

    def __repr__(self):
        entity = f"Player {self.player_id}" if self.player_id else f"Team {self.team_id}"
        return f'<GroupStanding Group {self.group_id} - {entity} - Pos {self.position}>'

class Match(db.Model):
    __tablename__ = 'match'
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('tournament_category.id'))
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=True) # Link to group if part of group stage

    # Dynamic properties for tracking match stage and round
    stage = db.Column(Enum(MatchStage), default=MatchStage.KNOCKOUT)
    round = db.Column(db.Integer)  # 1=final, 2=semifinal, etc. or group stage round number
    match_order = db.Column(db.Integer)  # Order within the round/group

    # Scheduling info
    court = db.Column(db.String(50), nullable=True) # Field exists and is properly named
    scheduled_time = db.Column(db.DateTime, nullable=True) # Field exists and is properly named
    livestream_url = db.Column(db.String(255), nullable=True) # Added from requirements

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
    next_match_id = db.Column(db.Integer, db.ForeignKey('match.id'), nullable=True) # For bracket progression

    # Verification flags (added from requirements)
    referee_verified = db.Column(db.Boolean, default=False)
    player_verified = db.Column(db.Boolean, default=False)
    
    # Position codes for players/teams (e.g., "A1", "B2" for groups, "1", "2" for knockout)
    player1_code = db.Column(db.String(10), nullable=True)
    player2_code = db.Column(db.String(10), nullable=True)

    # Relationships (use strings)
    scores = db.relationship('MatchScore', backref='match', lazy='dynamic', cascade='all, delete-orphan')
    # category relationship defined in TournamentCategory model via backref
    # group relationship defined in Group model via backref
    # player1_profile relationship defined in PlayerProfile model via backref
    # player2_profile relationship defined in PlayerProfile model via backref
    # team1_profile relationship defined in Team model via backref
    # team2_profile relationship defined in Team model via backref
    # winning_player_profile relationship defined in PlayerProfile model via backref
    # winning_team_profile relationship defined in Team model via backref
    # losing_player_profile relationship defined in PlayerProfile model via backref
    # losing_team_profile relationship defined in Team model via backref

    # Self-referential relationship for bracket progression
    next_match = db.relationship('Match', remote_side=[id], backref='previous_matches')

    player1 = db.relationship('PlayerProfile', foreign_keys=[player1_id], backref=db.backref('matches_as_player1_alt', lazy='dynamic'))
    player2 = db.relationship('PlayerProfile', foreign_keys=[player2_id], backref=db.backref('matches_as_player2_alt', lazy='dynamic'))
    team1 = db.relationship('Team', foreign_keys=[team1_id], backref=db.backref('matches_as_team1_alt', lazy='dynamic'))
    team2 = db.relationship('Team', foreign_keys=[team2_id], backref=db.backref('matches_as_team2_alt', lazy='dynamic'))

    @property
    def is_doubles(self):
        """Check if this is a doubles match based on category type"""
        # Ensure category is loaded if accessed this way
        if not self.category:
            # Attempt to load category if not already loaded (might incur DB hit)
            # Or handle cases where category might not be set yet
             return False # Or raise an error, depending on expected state
        return self.category.is_doubles()

    @property
    def round_name(self):
        """Get human-readable round name based on round number"""
        if self.stage == MatchStage.GROUP:
            group_name = self.group.name if self.group else ''
            return f"Group {group_name} Round"

        # Ensure round is not None
        if self.round is None:
            return "N/A"

        if self.round == 1:
            return "Final"
        elif self.round == 2:
            return "Semifinal"
        elif self.round == 1.5:
            return "Third Place Playoff"
        elif self.round == 3:
            return "Quarterfinal"
        elif self.round == 4:
            return "Round of 16"
        elif self.round == 5:
            return "Round of 32"
        elif self.round == 6:
            return "Round of 64"
        else:
            # Handle potentially large round numbers or playoff stages differently if needed
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
        """Get the winner (player or team object)"""
        if self.is_doubles:
            return self.winning_team_profile # Use backref name from Team model
        return self.winning_player_profile # Use backref name from PlayerProfile model

    @property
    def loser(self):
        """Get the loser (player or team object)"""
        if self.is_doubles:
            return self.losing_team_profile # Use backref name from Team model
        return self.losing_player_profile # Use backref name from PlayerProfile model

    def __repr__(self):
        return f'<Match {self.id} - Category {self.category_id} - Round {self.round}>'


class MatchScore(db.Model):
    __tablename__ = 'match_score'
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('match.id'))
    set_number = db.Column(db.Integer)
    # Renaming for clarity, assuming player1/team1 corresponds to player1_score
    player1_score = db.Column(db.Integer, default=0) # Score for player1/team1
    player2_score = db.Column(db.Integer, default=0) # Score for player2/team2
    # match relationship defined in Match model via backref

    def __repr__(self):
        return f'<MatchScore Match {self.match_id} Set {self.set_number}: {self.player1_score}-{self.player2_score}>'