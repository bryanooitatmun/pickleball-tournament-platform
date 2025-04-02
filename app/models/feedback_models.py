from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, String, Text, DateTime, Boolean
from sqlalchemy.orm import relationship
from app import db

class Feedback(db.Model):
    """
    Model for tournament/organizer feedback submitted by players.
    This is separate from the support ticket system and focused on ratings and reviews.
    """
    __tablename__ = 'feedback'
    id = db.Column(db.Integer, primary_key=True)
    
    # Who submitted the feedback
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # What the feedback is about (one or the other should be set)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=True)
    organizer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Feedback content
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    comment = db.Column(db.Text, nullable=True)
    
    # Privacy settings
    is_anonymous = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Moderation fields
    is_approved = db.Column(db.Boolean, default=True)
    is_featured = db.Column(db.Boolean, default=False)
    admin_notes = db.Column(db.Text, nullable=True)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='submitted_feedback')
    tournament = db.relationship('Tournament', backref='feedback')
    organizer = db.relationship('User', foreign_keys=[organizer_id], backref='received_feedback')
    
    def __repr__(self):
        target = f"Tournament {self.tournament_id}" if self.tournament_id else f"Organizer {self.organizer_id}"
        return f'<Feedback {self.id} by User {self.user_id} for {target}: {self.rating}/5>'
