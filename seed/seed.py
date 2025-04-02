from datetime import datetime, timedelta, date
from app import db, create_app
import sys
from app.models import Tournament, TournamentCategory, CategoryType, TournamentTier, TournamentFormat, TournamentStatus, Venue, User, UserRole, PrizeType, Prize, Registration, Team, Match, MatchScore, Group, GroupStanding
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import random
import string
import math

app = create_app()
app.app_context().push()

def seed_tournament():
    # Create or find the venue
    venue = Venue.query.filter_by(name="Oncourt Malaysia").first()
    if not venue:
        venue = Venue(
            name="Oncourt Malaysia",
            address="Combat Baze, Jalan Lapangan Terbang Lama, Pengkalan Tentera Udara Diraja Malaysia",
            city="Kuala Lumpur",
            state="Wilayah Persekutuan",
            country="Malaysia",
            postal_code="50460",
            description="Oncourt Malaysia's premier pickleball facility.",
            court_count=8
        )
        db.session.add(venue)
        db.session.commit()
    
    # Create or find an organizer (assuming there's an admin user)
    organizer = User.query.filter_by(role=UserRole.ADMIN).first()
    if not organizer:
        # If no admin exists, create one
        organizer = User.query.filter_by(role=UserRole.ORGANIZER).first()
        if not organizer:
            # If no organizer exists either, create one
            organizer = User(
                username="tournament_organizer",
                email="organizer@sportssync.com",
                role=UserRole.ORGANIZER
            )
            organizer.set_password("password123")
            db.session.add(organizer)
            db.session.commit()
    
    # Find the tournament or create it if it doesn't exist
    tournament = Tournament.query.filter_by(name="SportsSync-Oncourt Pickleball Tournament").first()
    
    if not tournament:
        # Create the tournament
        tournament = Tournament(
            name="SportsSync-Oncourt Pickleball Tournament",
            organizer_id=organizer.id,
            location="Combat Baze, Jalan Lapangan Terbang Lama, Pengkalan Tentera Udara Diraja Malaysia, 50460 Wilayah Persekutuan, Kuala Lumpur",
            description="SportsSync-Oncourt Pickleball Tournament 2025 is set to be Malaysia's premier pickleball event, bringing together players from across Southeast Asia to compete in 6 categories at Oncourt Malaysia.\n\nThe tournament will officially kick off on Day 1 (14 April 2025) at 8:00 am. More than just a tournament, it will be a captivating experience as the best players battle it out in an electrifying atmosphere, surrounded by world-class courts, passionate crowds, and the ultimate pickleball venue. With thrilling matches, exclusive gear drops, sponsor activations, and surprises along the way, this is one event you don't want to miss.\n\nTOURNAMENT SCHEDULE:\nDAY 1 - 14TH APRIL 2025 (FRIDAY)\n8:00am - 12:00pm: Mixed Doubles Intermediate\n12:00pm - 4:00pm: Men's Doubles Open\n4:00pm - 8:00pm: Women's Doubles Open\n\nDAY 2 - 15TH APRIL 2025 (SATURDAY)\n8:00am - 12:00pm: Women's Doubles Intermediate\n12:00pm - 4:00pm: Men's Doubles Intermediate\n4:00pm - 8:00pm: Mixed Doubles Open\n8:00pm - 10:00pm: After Party\n\nSCORING FORMAT:\nGroup Stage, Top 16 & Quarter Finals:\n- Open Events: Traditional Scoring to 11 points\n- Intermediate Events: Rally Scoring to 15 points\n\nSemi Finals:\n- Open Events: Traditional Scoring to 15 points\n- Intermediate Events: Rally Scoring to 21 points\n\n3rd/4th Placing Playoff & Final:\n- Open Events: Traditional Scoring to 21 points\n- Intermediate Events: Rally Scoring to 21 points\n\nNumber of Sets: 1 Set\n\nTime-Out:\n- 1 minute per team (1 time-out only) for Group Stage, Top 16 & Quarter Finals\n- 1 minute per team (2 time-outs) for Semi Finals, 3rd/4th Placing Playoff & Final\n\nJoin us for an exciting after-party following the tournament to celebrate with fellow pickleball enthusiasts!",
            start_date=datetime(2025, 4, 14, 8, 0, 0),  # April 14, 2025, 8:00 AM
            end_date=datetime(2025, 4, 15, 22, 0, 0),   # April 15, 2025, 10:00 PM (including after-party)
            registration_deadline=datetime(2025, 4, 7, 23, 59, 59),  # April 7, 2025, 11:59 PM
            tier=TournamentTier.OPEN,
            format=TournamentFormat.GROUP_KNOCKOUT,
            status=TournamentStatus.UPCOMING,  # Initially UPCOMING, will update to ONGOING later
            prize_pool=15000.00,  # Total prize pool
            venue_id=venue.id,
            is_featured=True,
            
            # New fields for prize structure
            total_cash_prize=15000.00,
            total_prize_value=20000.00,  # Cash + merchandise value
            prize_structure_description="Cash prizes and exclusive merchandise across all categories. Winners receive specially designed trophies and exclusive gear from our sponsors.",
            
            # Payment details
            payment_bank_name="Alliance Bank",
            payment_account_number="12345678",
            payment_account_name="SportsSync Sdn Bhd",
            payment_reference_prefix="SSOPT2025",
            
            # Door gifts and prizes
            door_gifts="COMPLIMENTARY FOR REGISTERED PLAYERS:\n1 x Limited Edition SportsSync x Protech Sports T-Shirt\nSportsSync-Oncourt Goodie Bag with sponsor giveaways\nComplimentary Team Photo Session by Canon\nAll matches will be recorded in the DUPR system"
        )
        db.session.add(tournament)
        db.session.flush()  # Flush to get the tournament ID without committing
        
        # Common intermediate eligibility rules
        intermediate_rules = "INTERMEDIATE CATEGORY ELIGIBILITY RULES:\n1) We will conduct thorough due diligence on every player.\n2) DUPR serves as an initial guideline but does not solely determine eligibility for the Intermediate category.\n3) We reserve the right to move players to the Open category if their skill level exceeds their current DUPR rating.\n4) Participants may report players they believe should be in the Open category. We will conduct due diligence, and the final decision will be made by management.\n5) Players who win any tournament, whether on Reclub or elsewhere, will be reviewed to determine their eligibility to compete in the Intermediate category.\n6) No refunds will be given if a player is moved from the Intermediate to the Open category.\n7) Players without a DUPR rating are welcome to participate in the Intermediate tournament, but due diligence will be conducted to assess their eligibility.\n8) If one player is deemed eligible for the Open category while their partner remains in the Intermediate category, the Intermediate player must find a replacement. Otherwise, the entire team will be moved to the Open category.\n9) If, during the tournament, we identify a team that was mistakenly placed in the Intermediate category but should be in the Open