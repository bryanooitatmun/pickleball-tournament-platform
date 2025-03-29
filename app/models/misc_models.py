from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, String, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from app import db

class Equipment(db.Model):
    __tablename__ = 'equipment'
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player_profile.id'))
    brand = db.Column(db.String(100))
    name = db.Column(db.String(200)) # e.g., Paddle model, Shoe model
    image = db.Column(db.String(255))
    buy_link = db.Column(db.String(255))

    # Relationships (use strings)
    # player relationship defined in PlayerProfile model via backref

    def __repr__(self):
        return f'<Equipment {self.name} for Player {self.player_id}>'


class Advertisement(db.Model):
    __tablename__ = 'advertisement'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    image = db.Column(db.String(255), nullable=False)
    link = db.Column(db.String(255))
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime)
    position = db.Column(db.String(50))  # 'hero', 'sidebar', 'footer', etc.
    is_active = db.Column(db.Boolean, default=True)
    views = db.Column(db.Integer, default=0) # Basic tracking
    clicks = db.Column(db.Integer, default=0) # Basic tracking

    def __repr__(self):
        return f'<Advertisement {self.id} - {self.title}>'