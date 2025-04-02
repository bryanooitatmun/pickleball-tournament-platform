from datetime import datetime
from sqlalchemy import Enum, Column, Integer, ForeignKey, String, Text, DateTime, Float
from sqlalchemy.orm import relationship
from app import db
from app.models.enums import PrizeType # Import necessary enums

class Prize(db.Model):
    __tablename__ = 'prize'
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('tournament_category.id'))
    placement = db.Column(db.String(20))  # "1", "2", "3-4", etc.
    prize_type = db.Column(Enum(PrizeType), default=PrizeType.CASH)

    # For cash prizes
    cash_amount = db.Column(db.Float, default=0.0)

    # For non-cash prizes (merchandise, vouchers)
    title = db.Column(db.String(100))  # "Pro Paddle", "Nike Shoes", "$50 Voucher" etc.
    description = db.Column(db.Text, nullable=True)
    image = db.Column(db.String(255), nullable=True)
    monetary_value = db.Column(db.Float, default=0.0)  # Estimated value
    quantity = db.Column(db.Integer, default=1)

    # For vouchers/gift cards specifically
    vendor = db.Column(db.String(100), nullable=True)
    expiry_date = db.Column(db.DateTime, nullable=True)

    # For sponsored products
    sponsor_id = db.Column(db.Integer, db.ForeignKey('platform_sponsor.id'), nullable=True)

    # Relationships (use strings)
    # category relationship defined in TournamentCategory model via backref
    # sponsor relationship defined in PlatformSponsor model via backref

    def __repr__(self):
        return f'<Prize {self.id} - {self.title or f"Cash ${self.cash_amount}"} for Place {self.placement}>'