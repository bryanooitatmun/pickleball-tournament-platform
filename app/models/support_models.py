from datetime import datetime
from sqlalchemy import Enum, Column, Integer, ForeignKey, String, Text, DateTime
from sqlalchemy.orm import relationship
from app import db
from app.models.enums import TicketType, TicketStatus # Import necessary enums

class SupportTicket(db.Model):
    __tablename__ = 'support_ticket'
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=True) # Optional link to tournament
    submitter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reported_player_id = db.Column(db.Integer, db.ForeignKey('player_profile.id'), nullable=True) # For player reports
    ticket_type = db.Column(Enum(TicketType), default=TicketType.GENERAL_SUPPORT)
    status = db.Column(Enum(TicketStatus), default=TicketStatus.OPEN)
    subject = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships (use strings)
    # tournament relationship defined in Tournament model via backref
    # submitter relationship defined in User model via backref
    # reported_player relationship defined in PlayerProfile model via backref
    responses = db.relationship('TicketResponse', backref='ticket', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<SupportTicket {self.id} - {self.subject}>'

class TicketResponse(db.Model):
    __tablename__ = 'ticket_response'
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_ticket.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # User who wrote the response
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships (use strings)
    # ticket relationship defined in SupportTicket model via backref
    # user relationship defined in User model via backref

    def __repr__(self):
        return f'<TicketResponse {self.id} for Ticket {self.ticket_id}>'