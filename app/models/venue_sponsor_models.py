from datetime import datetime
from sqlalchemy import Enum, Table, Column, Integer, ForeignKey, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from app import db
from app.models.enums import SponsorTier # Import necessary enums

class VenueImage(db.Model):
    __tablename__ = 'venue_image'
    id = db.Column(db.Integer, primary_key=True)
    venue_id = db.Column(db.Integer, db.ForeignKey('venue.id'), nullable=False)
    image_path = db.Column(db.String(255), nullable=False)
    caption = db.Column(db.String(255))
    display_order = db.Column(db.Integer, default=999)
    is_primary = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship with venue (use string)
    # venue relationship defined in Venue model via backref

    def __repr__(self):
        return f'<VenueImage {self.id} for Venue {self.venue_id}>'

class Venue(db.Model):
    __tablename__ = 'venue'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(255))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    country = db.Column(db.String(100))
    description = db.Column(db.Text)
    image = db.Column(db.String(255))  # Legacy field, consider removing if primary_image logic is stable
    website = db.Column(db.String(255))
    postal_code = db.Column(db.String(20))
    is_featured = db.Column(db.Boolean, default=False)
    court_count = db.Column(db.Integer, default=0)

    # New fields
    contact_email = db.Column(db.String(100))
    contact_phone = db.Column(db.String(50))
    facilities = db.Column(db.Text)  # Consider using JSON type if DB supports it
    amenities = db.Column(db.Text)  # Consider using JSON type if DB supports it
    parking_info = db.Column(db.Text)
    google_maps_url = db.Column(db.String(255))
    display_order = db.Column(db.Integer, default=999)

    # Relationships (use strings)
    images = db.relationship('VenueImage', backref='venue', lazy='dynamic', cascade='all, delete-orphan', order_by='VenueImage.display_order')
    tournaments = db.relationship('Tournament', backref='venue', lazy='dynamic')

    @property
    def primary_image(self):
        """Return the primary image path for this venue"""
        # Use the relationship which is ordered
        primary = next((img for img in self.images if img.is_primary), None)
        if primary:
            return primary.image_path
        # Fallback to the first image if no primary is set
        first_image = self.images.first()
        if first_image:
            return first_image.image_path
        # Fallback to the old image field if no images in the new relationship
        return self.image

    @property
    def gallery_images(self):
        """Return all images for gallery display, ordered by display_order"""
        # The relationship is already ordered
        return self.images.all()

    def __repr__(self):
        return f'<Venue {self.name}>'

# Association table for tournament sponsors
tournament_sponsors = db.Table('tournament_sponsors',
    db.Column('tournament_id', db.Integer, db.ForeignKey('tournament.id'), primary_key=True),
    db.Column('sponsor_id', db.Integer, db.ForeignKey('platform_sponsor.id'), primary_key=True)
)

class PlatformSponsor(db.Model):
    __tablename__ = 'platform_sponsor'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    logo = db.Column(db.String(255))
    website = db.Column(db.String(255))
    is_featured = db.Column(db.Boolean, default=False)
    tier = db.Column(Enum(SponsorTier), default=SponsorTier.SUPPORTING)
    description = db.Column(db.Text)
    display_order = db.Column(db.Integer, default=999)

    # Additional fields
    contact_name = db.Column(db.String(100))
    contact_email = db.Column(db.String(100))
    contact_phone = db.Column(db.String(50))
    banner_image = db.Column(db.String(255))

    # Relationships (use strings)
    tournaments = db.relationship('Tournament', secondary=tournament_sponsors, backref='platform_sponsors')
    sponsored_prizes = db.relationship('Prize', backref='sponsor', lazy='dynamic')

    def __repr__(self):
        tier_value = self.tier.value if self.tier else "No Tier"
        return f'<PlatformSponsor {self.name} - {tier_value}>'


class PlayerSponsor(db.Model):
    __tablename__ = 'player_sponsor'
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player_profile.id'))
    name = db.Column(db.String(100))
    logo = db.Column(db.String(255))
    link = db.Column(db.String(255))

    # Relationships (use strings)
    # player relationship defined in PlayerProfile model via backref

    def __repr__(self):
        return f'<PlayerSponsor {self.name} for Player {self.player_id}>'