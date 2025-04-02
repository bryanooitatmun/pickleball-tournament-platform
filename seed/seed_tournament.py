"""
Seed script for creating tournaments, categories, venues, and prizes.
Creates multiple tournaments with categories and related prizes.
"""

from app.models import (
    Tournament, TournamentCategory, CategoryType, TournamentTier, 
    TournamentFormat, TournamentStatus, Venue, PrizeType, Prize, User, UserRole
)
from .seed_base import app, db, commit_changes, generate_reference
from .seed_users import create_organizer
from datetime import datetime, timedelta
import sys
import random

def create_venue_generic(name, address, city, state, country, postal_code, description, court_count, commit=True):
    """Create a venue with the given parameters"""
    # Check if venue exists
    venue = Venue.query.filter_by(name=name).first()
    if venue:
        print(f"Venue '{name}' already exists")
        return venue
    
    venue = Venue(
        name=name,
        address=address,
        city=city,
        state=state,
        country=country,
        postal_code=postal_code,
        description=description,
        court_count=court_count
    )
    db.session.add(venue)
    
    if commit:
        commit_changes(f"Venue '{name}' created")
    
    return venue

def create_oncourt_venue(commit=True):
    """Create the Oncourt Malaysia venue"""
    return create_venue_generic(
        name="Oncourt Malaysia",
        address="Combat Baze, Jalan Lapangan Terbang Lama, Pengkalan Tentera Udara Diraja Malaysia",
        city="Kuala Lumpur",
        state="Wilayah Persekutuan",
        country="Malaysia",
        postal_code="50460",
        description="Oncourt Malaysia's premier pickleball facility.",
        court_count=8,
        commit=commit
    )

def create_pickletime_venue(commit=True):
    """Create the PickleTime venue"""
    return create_venue_generic(
        name="PickleTime",
        address="854, Jalan Subang 7, Taman Indah Subang Uep",
        city="Subang Jaya",
        state="Selangor",
        country="Malaysia",
        postal_code="47630",
        description="PickleTime's state-of-the-art pickleball facility.",
        court_count=10,
        commit=commit
    )

def add_prizes_to_category(category, prizes, commit=False):
    """Helper function to add prizes to a category"""
    for prize_data in prizes:
        prize_type = prize_data["type"]
        placement = prize_data["placement"]
        
        prize = Prize(
            category_id=category.id,
            placement=placement,
            prize_type=prize_type
        )
        
        # Set specific fields based on prize type
        if prize_type == PrizeType.CASH:
            prize.cash_amount = prize_data["amount"]
        elif prize_type in [PrizeType.MERCHANDISE]:
            prize.title = prize_data["title"]
            prize.description = prize_data.get("description")
            prize.monetary_value = prize_data.get("value", 0.0)
            prize.quantity = prize_data.get("quantity", 1)
            if "vendor" in prize_data:
                prize.vendor = prize_data["vendor"]
            if "expiry_date" in prize_data:
                prize.expiry_date = prize_data["expiry_date"]
        
        db.session.add(prize)
    
    if commit:
        commit_changes("Prizes added to category")

def create_sportssync_oncourt_tournament(status=TournamentStatus.ONGOING, commit=True):
    """Create the SportsSync-Oncourt Pickleball Tournament with categories and prizes"""
    # Get or create organizer
    organizer = User.query.filter_by(role=UserRole.ORGANIZER).first()
    if not organizer:
        organizer = create_organizer(commit=False)
    
    # Get or create venue
    venue = create_oncourt_venue(commit=False)
    
    # Check if tournament exists
    tournament = Tournament.query.filter_by(name="SportsSync-Oncourt Pickleball Tournament").first()
    if tournament:
        print("Tournament 'SportsSync-Oncourt Pickleball Tournament' already exists")
        # Update status if needed
        if tournament.status != status:
            tournament.status = status
            if commit:
                commit_changes(f"Tournament status updated to {status.name}")
        return tournament
    
    # Create tournament
    tournament = Tournament(
        name="SportsSync-Oncourt Pickleball Tournament",
        organizer_id=organizer.id,
        location=venue.address + ", " + venue.postal_code + " " + venue.state + ", " + venue.city,
        description="SportsSync-Oncourt Pickleball Tournament 2025 is set to be Malaysia's premier pickleball event, bringing together players from across Southeast Asia to compete in 6 categories at Oncourt Malaysia.\n\nThe tournament will officially kick off on Day 1 (14 April 2025) at 8:00 am. More than just a tournament, it will be a captivating experience as the best players battle it out in an electrifying atmosphere, surrounded by world-class courts, passionate crowds, and the ultimate pickleball venue. With thrilling matches, exclusive gear drops, sponsor activations, and surprises along the way, this is one event you don't want to miss.\n\nTOURNAMENT SCHEDULE:\nDAY 1 - 14TH APRIL 2025 (FRIDAY)\n8:00am - 12:00pm: Mixed Doubles Intermediate\n12:00pm - 4:00pm: Men's Doubles Open\n4:00pm - 8:00pm: Women's Doubles Open\n\nDAY 2 - 15TH APRIL 2025 (SATURDAY)\n8:00am - 12:00pm: Women's Doubles Intermediate\n12:00pm - 4:00pm: Men's Doubles Intermediate\n4:00pm - 8:00pm: Mixed Doubles Open\n8:00pm - 10:00pm: After Party\n\nSCORING FORMAT:\nGroup Stage, Top 16 & Quarter Finals:\n- Open Events: Traditional Scoring to 11 points\n- Intermediate Events: Rally Scoring to 15 points\n\nSemi Finals:\n- Open Events: Traditional Scoring to 15 points\n- Intermediate Events: Rally Scoring to 21 points\n\n3rd/4th Placing Playoff & Final:\n- Open Events: Traditional Scoring to 21 points\n- Intermediate Events: Rally Scoring to 21 points\n\nNumber of Sets: 1 Set\n\nTime-Out:\n- 1 minute per team (1 time-out only) for Group Stage, Top 16 & Quarter Finals\n- 1 minute per team (2 time-outs) for Semi Finals, 3rd/4th Placing Playoff & Final\n\nJoin us for an exciting after-party following the tournament to celebrate with fellow pickleball enthusiasts!",
        start_date=datetime(2025, 4, 14, 8, 0, 0),  # April 14, 2025, 8:00 AM
        end_date=datetime(2025, 4, 15, 22, 0, 0),   # April 15, 2025, 10:00 PM (including after-party)
        registration_deadline=datetime(2025, 4, 7, 23, 59, 59),  # April 7, 2025, 11:59 PM
        tier=TournamentTier.OPEN,
        format=TournamentFormat.GROUP_KNOCKOUT,
        status=status,
        prize_pool=15000.00,  # Total prize pool
        venue_id=venue.id,
        is_featured=True,
        
        # Prize structure
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
    db.session.flush()  # Get tournament ID without committing
    
    # Common intermediate eligibility rules
    intermediate_rules = "INTERMEDIATE CATEGORY ELIGIBILITY RULES:\n1) We will conduct thorough due diligence on every player.\n2) DUPR serves as an initial guideline but does not solely determine eligibility for the Intermediate category.\n3) We reserve the right to move players to the Open category if their skill level exceeds their current DUPR rating.\n4) Participants may report players they believe should be in the Open category. We will conduct due diligence, and the final decision will be made by management.\n5) Players who win any tournament, whether on Reclub or elsewhere, will be reviewed to determine their eligibility to compete in the Intermediate category.\n6) No refunds will be given if a player is moved from the Intermediate to the Open category.\n7) Players without a DUPR rating are welcome to participate in the Intermediate tournament, but due diligence will be conducted to assess their eligibility.\n8) If one player is deemed eligible for the Open category while their partner remains in the Intermediate category, the Intermediate player must find a replacement. Otherwise, the entire team will be moved to the Open category.\n9) If, during the tournament, we identify a team that was mistakenly placed in the Intermediate category but should be in the Open category, they may continue playing. However, if they finish in first place, their points will not be counted in the ranking system. They will still receive the prize and medals."
    
    # Create tournament categories
    categories = [
        # Mixed Doubles Open
        TournamentCategory(
            tournament_id=tournament.id,
            category_type=CategoryType.MIXED_DOUBLES,
            name="Mixed Doubles Open",
            max_participants=64,  # 32 teams
            points_awarded=1000,
            format=TournamentFormat.GROUP_KNOCKOUT,
            registration_fee=300.00,  # RM300 per team
            prize_percentage=25,  # 25% of total prize pool
            gender_restriction="mixed",
            prize_distribution={"1": 50, "2": 30, "3": 20},
            points_distribution={"1": 100, "2": 70, "3-4": 50, "5-8": 30, "9-16": 15},
            prize_money=3500.00,
            has_merchandise=True,
            has_trophies=True,
            prize_summary="Grand Prize: RM3,500 cash + RM1,500 worth of exclusive merchandise\nFirst Runner-Up: RM2,500 cash + RM1,000 worth of exclusive merchandise\nSecond Runner-Up: RM1,500 cash + RM800 worth of exclusive merchandise",
            total_prize_value=9700.00,
            display_order=10,
        ),
        
        # Mixed Doubles Intermediate
        TournamentCategory(
            tournament_id=tournament.id,
            category_type=CategoryType.MIXED_DOUBLES,
            name="Mixed Doubles Intermediate",
            max_participants=64,  # 32 teams
            points_awarded=500,
            format=TournamentFormat.GROUP_KNOCKOUT,
            registration_fee=240.00,  # RM240 per team
            prize_percentage=15,  # 15% of total prize pool
            gender_restriction="mixed",
            max_dupr_rating=3.5,  # Max DUPR rating for Intermediate
            prize_distribution={"1": 50, "2": 30, "3": 20},
            points_distribution={"1": 100, "2": 70, "3-4": 50, "5-8": 30, "9-16": 15},
            prize_money=1600.00,
            has_merchandise=True,
            has_trophies=True,
            description=intermediate_rules,
            prize_summary="Grand Prize: RM1,600 cash + RM1,000 worth of exclusive merchandise\nFirst Runner-Up: RM1,100 cash + RM700 worth of exclusive merchandise\nSecond Runner-Up: RM700 cash + RM300 worth of exclusive merchandise",
            total_prize_value=4400.00,
            display_order=40,
        ),
        
        # Women's Doubles Open
        TournamentCategory(
            tournament_id=tournament.id,
            category_type=CategoryType.WOMENS_DOUBLES,
            name="Women's Doubles Open",
            max_participants=48,  # 24 teams
            points_awarded=1000,
            format=TournamentFormat.GROUP_KNOCKOUT,
            registration_fee=300.00,  # RM300 per team
            prize_percentage=15,  # 15% of total prize pool
            gender_restriction="female",
            prize_distribution={"1": 50, "2": 30, "3": 20},
            points_distribution={"1": 100, "2": 70, "3-4": 50, "5-8": 30, "9-16": 15},
            prize_money=3500.00,
            has_merchandise=True,
            has_trophies=True,
            prize_summary="Grand Prize: RM3,500 cash + RM1,500 worth of exclusive merchandise\nFirst Runner-Up: RM2,500 cash + RM1,000 worth of exclusive merchandise\nSecond Runner-Up: RM1,500 cash + RM800 worth of exclusive merchandise",
            total_prize_value=9700.00,
            display_order=20,
        ),
        
        # Women's Doubles Intermediate
        TournamentCategory(
            tournament_id=tournament.id,
            category_type=CategoryType.WOMENS_DOUBLES,
            name="Women's Doubles Intermediate",
            max_participants=48,  # 24 teams
            points_awarded=500,
            format=TournamentFormat.GROUP_KNOCKOUT,
            registration_fee=240.00,  # RM240 per team
            prize_percentage=10,  # 10% of total prize pool
            gender_restriction="female",
            max_dupr_rating=3.5,  # Max DUPR rating for Intermediate
            prize_distribution={"1": 50, "2": 30, "3": 20},
            points_distribution={"1": 100, "2": 70, "3-4": 50, "5-8": 30, "9-16": 15},
            prize_money=1600.00,
            has_merchandise=True,
            has_trophies=True,
            description=intermediate_rules,
            prize_summary="Grand Prize: RM1,600 cash + RM1,000 worth of exclusive merchandise\nFirst Runner-Up: RM1,100 cash + RM700 worth of exclusive merchandise\nSecond Runner-Up: RM700 cash + RM300 worth of exclusive merchandise",
            total_prize_value=4400.00,
            display_order=50,
        ),
        
        # Men's Doubles Open
        TournamentCategory(
            tournament_id=tournament.id,
            category_type=CategoryType.MENS_DOUBLES,
            name="Men's Doubles Open",
            max_participants=64,  # 32 teams
            points_awarded=1000,
            format=TournamentFormat.GROUP_KNOCKOUT,
            registration_fee=300.00,  # RM300 per team
            prize_percentage=25,  # 25% of total prize pool
            gender_restriction="male",
            prize_distribution={"1": 50, "2": 30, "3": 20},
            points_distribution={"1": 100, "2": 70, "3-4": 50, "5-8": 30, "9-16": 15},
            prize_money=3500.00,
            has_merchandise=True,
            has_trophies=True,
            prize_summary="Grand Prize: RM3,500 cash + RM1,500 worth of exclusive merchandise\nFirst Runner-Up: RM2,500 cash + RM1,000 worth of exclusive merchandise\nSecond Runner-Up: RM1,500 cash + RM800 worth of exclusive merchandise",
            total_prize_value=9700.00,
            display_order=1,
        ),
        
        # Men's Doubles Intermediate
        TournamentCategory(
            tournament_id=tournament.id,
            category_type=CategoryType.MENS_DOUBLES,
            name="Men's Doubles Intermediate",
            max_participants=64,  # 32 teams
            points_awarded=500,
            format=TournamentFormat.GROUP_KNOCKOUT,
            registration_fee=240.00,  # RM240 per team
            prize_percentage=10,  # 10% of total prize pool
            gender_restriction="male",
            max_dupr_rating=3.5,  # Max DUPR rating for Intermediate
            prize_distribution={"1": 50, "2": 30, "3": 20},
            points_distribution={"1": 100, "2": 70, "3-4": 50, "5-8": 30, "9-16": 15},
            prize_money=1600.00,
            has_merchandise=True,
            has_trophies=True,
            description=intermediate_rules,
            prize_summary="Grand Prize: RM1,600 cash + RM1,000 worth of exclusive merchandise\nFirst Runner-Up: RM1,100 cash + RM700 worth of exclusive merchandise\nSecond Runner-Up: RM700 cash + RM300 worth of exclusive merchandise",
            total_prize_value=4400.00,
            display_order=30,
        ),
    ]
    
    # Add categories to database
    for category in categories:
        db.session.add(category)
    
    # Flush to get category IDs
    db.session.flush()
    
    # Add prizes to categories
    # For Open Categories
    for category in [categories[0], categories[2], categories[4]]:  # Mixed Open, Women's Open, Men's Open
        add_prizes_to_category(category, [
            # Cash prizes
            {"placement": "1", "type": PrizeType.CASH, "amount": 3500.00},
            {"placement": "2", "type": PrizeType.CASH, "amount": 2500.00},
            {"placement": "3", "type": PrizeType.CASH, "amount": 750.00},
            
            # Merchandise prizes
            {"placement": "1", "type": PrizeType.MERCHANDISE, "title": "Exclusive Merchandise Package", 
                "description": "Premium pickleball gear and exclusive merchandise", 
                "value": 1500.00},
            {"placement": "2", "type": PrizeType.MERCHANDISE, "title": "Exclusive Merchandise Package", 
                "description": "High-quality pickleball gear and exclusive merchandise", 
                "value": 1000.00},
            {"placement": "3", "type": PrizeType.MERCHANDISE, "title": "Exclusive Merchandise Package", 
                "description": "Selected pickleball accessories and merchandise", 
                "value": 400.00}
        ], commit=False)
    
    # For Intermediate Categories
    for category in [categories[1], categories[3], categories[5]]:  # Mixed Int, Women's Int, Men's Int
        add_prizes_to_category(category, [
            # Cash prizes
            {"placement": "1", "type": PrizeType.CASH, "amount": 1600.00},
            {"placement": "2", "type": PrizeType.CASH, "amount": 1100.00},
            {"placement": "3", "type": PrizeType.CASH, "amount": 350.00},
            
            # Merchandise prizes
            {"placement": "1", "type": PrizeType.MERCHANDISE, "title": "Exclusive Merchandise Package", 
                "description": "Quality pickleball gear and exclusive merchandise", 
                "value": 1000.00},
            {"placement": "2", "type": PrizeType.MERCHANDISE, "title": "Exclusive Merchandise Package", 
                "description": "Selected pickleball gear and merchandise", 
                "value": 700.00},
            {"placement": "3", "type": PrizeType.MERCHANDISE, "title": "Exclusive Merchandise Package", 
                "description": "Branded merchandise and accessories", 
                "value": 150.00}
        ], commit=False)
    
    if commit:
        commit_changes("Tournament with categories and prizes created successfully")
    
    return tournament

def create_sportssync_cup_tournament(status=TournamentStatus.UPCOMING, commit=True):
    """Create the SportsSync Cup tournament with categories and prizes"""
    # Get or create organizer
    organizer = User.query.filter_by(role=UserRole.ORGANIZER).first()
    if not organizer:
        organizer = create_organizer(commit=False)
    
    # Get or create venue
    venue = create_pickletime_venue(commit=False)
    
    # Check if tournament exists
    tournament = Tournament.query.filter_by(name="SportsSync Cup").first()
    if tournament:
        print("Tournament 'SportsSync Cup' already exists")
        # Update status if needed
        if tournament.status != status:
            tournament.status = status
            if commit:
                commit_changes(f"Tournament status updated to {status.name}")
        return tournament
    
    # Create tournament
    tournament = Tournament(
        name="SportsSync Cup",
        organizer_id=organizer.id,
        location=venue.address + ", " + venue.postal_code + " " + venue.state + ", " + venue.city,
        description="The inaugural SportsSync Cup 2025 promises to be an exciting day of pickleball competition at the state-of-the-art PickleTime facility in Subang Jaya. This one-day tournament brings together players of all levels to compete in 4 exciting categories.\n\nThe tournament will start on May 1st, 2025 at 8:00 am. Experience the thrill of competition in a friendly, vibrant atmosphere with top-notch courts and passionate players. With exciting matches, great prizes, and an awesome community atmosphere, this is the perfect event for pickleball enthusiasts.\n\nTOURNAMENT SCHEDULE:\nMAY 1ST, 2025 (THURSDAY)\n8:00am - 12:00pm: Men's Doubles Open & Women's Doubles Open\n12:00pm - 4:00pm: Mixed Doubles Open & Mixed Doubles Intermediate\n4:00pm - 6:00pm: Finals for all categories\n6:00pm - 8:00pm: Prize giving ceremony and networking dinner\n\nSCORING FORMAT:\nGroup Stage & Quarter Finals:\n- All Events: Rally Scoring to 15 points\n\nSemi Finals & Finals:\n- All Events: Rally Scoring to 21 points\n\nNumber of Sets: 1 Set\n\nTime-Out:\n- 1 minute per team (1 time-out only) for all matches\n\nJoin us for a networking dinner after the tournament to connect with fellow pickleball enthusiasts!",
        start_date=datetime(2025, 5, 1, 8, 0, 0),  # May 1, 2025, 8:00 AM
        end_date=datetime(2025, 5, 1, 20, 0, 0),   # May 1, 2025, 8:00 PM (including dinner)
        registration_deadline=datetime(2025, 4, 24, 23, 59, 59),  # April 24, 2025, 11:59 PM
        tier=TournamentTier.OPEN,
        format=TournamentFormat.GROUP_KNOCKOUT,
        status=status,
        prize_pool=10000.00,  # Total prize pool
        venue_id=venue.id,
        is_featured=True,
        
        # Prize structure
        total_cash_prize=10000.00,
        total_prize_value=12000.00,  # Cash + merchandise value
        prize_structure_description="Cash prizes and quality merchandise for all categories. Winners receive custom SportsSync Cup trophies and special branded merchandise.",
        
        # Payment details
        payment_bank_name="CIMB Bank",
        payment_account_number="87654321",
        payment_account_name="SportsSync Sdn Bhd",
        payment_reference_prefix="SSCUP2025",
        
        # Door gifts and prizes
        door_gifts="COMPLIMENTARY FOR REGISTERED PLAYERS:\n1 x SportsSync Cup 2025 T-Shirt\nSportsSync Cup Goodie Bag with sponsor items\nComplimentary professional action shots\nAll matches will be recorded in the DUPR system"
    )
    db.session.add(tournament)
    db.session.flush()  # Get tournament ID without committing
    
    # Common intermediate eligibility rules
    intermediate_rules = "INTERMEDIATE CATEGORY ELIGIBILITY RULES:\n1) We will conduct thorough due diligence on every player.\n2) DUPR serves as an initial guideline but does not solely determine eligibility for the Intermediate category.\n3) We reserve the right to move players to the Open category if their skill level exceeds their current DUPR rating.\n4) Participants may report players they believe should be in the Open category. We will conduct due diligence, and the final decision will be made by management.\n5) Players who win any tournament, whether on Reclub or elsewhere, will be reviewed to determine their eligibility to compete in the Intermediate category.\n6) No refunds will be given if a player is moved from the Intermediate to the Open category.\n7) Players without a DUPR rating are welcome to participate in the Intermediate tournament, but due diligence will be conducted to assess their eligibility."
    
    # Create tournament categories
    categories = [
        # Mixed Doubles Open
        TournamentCategory(
            tournament_id=tournament.id,
            category_type=CategoryType.MIXED_DOUBLES,
            name="Mixed Doubles Open",
            max_participants=48,  # 24 teams
            points_awarded=800,
            format=TournamentFormat.GROUP_KNOCKOUT,
            registration_fee=250.00,  # RM250 per team
            prize_percentage=30,  # 30% of total prize pool
            gender_restriction="mixed",
            prize_distribution={"1": 50, "2": 30, "3": 20},
            points_distribution={"1": 100, "2": 70, "3-4": 50, "5-8": 30, "9-16": 15},
            prize_money=3000.00,
            has_merchandise=True,
            has_trophies=True,
            prize_summary="Grand Prize: RM3,000 cash + RM500 worth of merchandise\nFirst Runner-Up: RM1,800 cash + RM300 worth of merchandise\nSecond Runner-Up: RM1,200 cash + RM200 worth of merchandise",
            total_prize_value=7000.00,
            display_order=1,
        ),
        
        # Mixed Doubles Intermediate
        TournamentCategory(
            tournament_id=tournament.id,
            category_type=CategoryType.MIXED_DOUBLES,
            name="Mixed Doubles Intermediate",
            max_participants=48,  # 24 teams
            points_awarded=400,
            format=TournamentFormat.GROUP_KNOCKOUT,
            registration_fee=200.00,  # RM200 per team
            prize_percentage=20,  # 20% of total prize pool
            gender_restriction="mixed",
            max_dupr_rating=3.5,  # Max DUPR rating for Intermediate
            prize_distribution={"1": 50, "2": 30, "3": 20},
            points_distribution={"1": 100, "2": 70, "3-4": 50, "5-8": 30, "9-16": 15},
            prize_money=2000.00,
            has_merchandise=True,
            has_trophies=True,
            description=intermediate_rules,
            prize_summary="Grand Prize: RM1,000 cash + RM300 worth of merchandise\nFirst Runner-Up: RM600 cash + RM200 worth of merchandise\nSecond Runner-Up: RM400 cash + RM100 worth of merchandise",
            total_prize_value=2600.00,
            display_order=4,
        ),
        
        # Women's Doubles Open
        TournamentCategory(
            tournament_id=tournament.id,
            category_type=CategoryType.WOMENS_DOUBLES,
            name="Women's Doubles Open",
            max_participants=32,  # 16 teams
            points_awarded=800,
            format=TournamentFormat.GROUP_KNOCKOUT,
            registration_fee=250.00,  # RM250 per team
            prize_percentage=25,  # 25% of total prize pool
            gender_restriction="female",
            prize_distribution={"1": 50, "2": 30, "3": 20},
            points_distribution={"1": 100, "2": 70, "3-4": 50, "5-8": 30, "9-16": 15},
            prize_money=2500.00,
            has_merchandise=True,
            has_trophies=True,
            prize_summary="Grand Prize: RM1,250 cash + RM400 worth of merchandise\nFirst Runner-Up: RM750 cash + RM250 worth of merchandise\nSecond Runner-Up: RM500 cash + RM150 worth of merchandise",
            total_prize_value=3300.00,
            display_order=3,
        ),
        
        # Men's Doubles Open
        TournamentCategory(
            tournament_id=tournament.id,
            category_type=CategoryType.MENS_DOUBLES,
            name="Men's Doubles Open",
            max_participants=48,  # 24 teams
            points_awarded=800,
            format=TournamentFormat.GROUP_KNOCKOUT,
            registration_fee=250.00,  # RM250 per team
            prize_percentage=25,  # 25% of total prize pool
            gender_restriction="male",
            prize_distribution={"1": 50, "2": 30, "3": 20},
            points_distribution={"1": 100, "2": 70, "3-4": 50, "5-8": 30, "9-16": 15},
            prize_money=2500.00,
            has_merchandise=True,
            has_trophies=True,
            prize_summary="Grand Prize: RM1,250 cash + RM400 worth of merchandise\nFirst Runner-Up: RM750 cash + RM250 worth of merchandise\nSecond Runner-Up: RM500 cash + RM150 worth of merchandise",
            total_prize_value=3300.00,
            display_order=2,
        ),
    ]
    
    # Add categories to database
    for category in categories:
        db.session.add(category)
    
    # Flush to get category IDs
    db.session.flush()
    
    # Add prizes to categories
    for category in [categories[0]]:  # Mixed Open
        add_prizes_to_category(category, [
            # Cash prizes
            {"placement": "1", "type": PrizeType.CASH, "amount": 3000.00},
            {"placement": "2", "type": PrizeType.CASH, "amount": 1800.00},
            {"placement": "3", "type": PrizeType.CASH, "amount": 1200.00},
            
            # Merchandise prizes
            {"placement": "1", "type": PrizeType.MERCHANDISE, "title": "Premium Merchandise Package", 
                "description": "Top-tier pickleball gear and exclusive merchandise", 
                "value": 500.00},
            {"placement": "2", "type": PrizeType.MERCHANDISE, "title": "Premium Merchandise Package", 
                "description": "Quality pickleball gear and premium merchandise", 
                "value": 300.00},
            {"placement": "3", "type": PrizeType.MERCHANDISE, "title": "Premium Merchandise Package", 
                "description": "Selected pickleball accessories and merchandise", 
                "value": 200.00}
        ], commit=False)
    
    for category in [categories[1]]:  # Mixed Intermediate
        add_prizes_to_category(category, [
            # Cash prizes
            {"placement": "1", "type": PrizeType.CASH, "amount": 1000.00},
            {"placement": "2", "type": PrizeType.CASH, "amount": 600.00},
            {"placement": "3", "type": PrizeType.CASH, "amount": 400.00},
            
            # Merchandise prizes
            {"placement": "1", "type": PrizeType.MERCHANDISE, "title": "Merchandise Package", 
                "description": "Quality pickleball gear and merchandise", 
                "value": 300.00},
            {"placement": "2", "type": PrizeType.MERCHANDISE, "title": "Merchandise Package", 
                "description": "Selected pickleball accessories", 
                "value": 200.00},
            {"placement": "3", "type": PrizeType.MERCHANDISE, "title": "Merchandise Package", 
                "description": "Branded merchandise and accessories", 
                "value": 100.00}
        ], commit=False)
    
    for category in [categories[2], categories[3]]:  # Women's Open, Men's Open
        add_prizes_to_category(category, [
            # Cash prizes
            {"placement": "1", "type": PrizeType.CASH, "amount": 1250.00},
            {"placement": "2", "type": PrizeType.CASH, "amount": 750.00},
            {"placement": "3", "type": PrizeType.CASH, "amount": 500.00},
            
            # Merchandise prizes
            {"placement": "1", "type": PrizeType.MERCHANDISE, "title": "Premium Merchandise Package", 
                "description": "Quality pickleball gear and exclusive merchandise", 
                "value": 400.00},
            {"placement": "2", "type": PrizeType.MERCHANDISE, "title": "Premium Merchandise Package", 
                "description": "Selected pickleball gear and merchandise", 
                "value": 250.00},
            {"placement": "3", "type": PrizeType.MERCHANDISE, "title": "Premium Merchandise Package", 
                "description": "Branded merchandise and accessories", 
                "value": 150.00}
        ], commit=False)
    
    if commit:
        commit_changes("Tournament 'SportsSync Cup' with categories and prizes created successfully")
    
    return tournament

def main():
    """Run when this script is executed directly"""
    # Create first tournament - SportsSync-Oncourt Pickleball Tournament
    tournament1 = create_sportssync_oncourt_tournament(status=TournamentStatus.ONGOING)
    print(f"Tournament '{tournament1.name}' created with status '{tournament1.status.name}'")
    print(f"Tournament has {tournament1.categories.count()} categories")
    
    # Create second tournament - SportsSync Cup
    tournament2 = create_sportssync_cup_tournament(status=TournamentStatus.UPCOMING)
    print(f"Tournament '{tournament2.name}' created with status '{tournament2.status.name}'")
    print(f"Tournament has {tournament2.categories.count()} categories")

if __name__ == "__main__":
    with app.app_context():
        main()
