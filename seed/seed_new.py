from datetime import datetime, timedelta, date
from app import db, create_app
import sys
from app.models import Tournament, TournamentCategory, CategoryType, TournamentTier, TournamentFormat, TournamentStatus, Venue, User, UserRole, PrizeType, Prize, Registration, Team, Match, MatchScore, Group, GroupStanding
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
        intermediate_rules = "INTERMEDIATE CATEGORY ELIGIBILITY RULES:\n1) We will conduct thorough due diligence on every player.\n2) DUPR serves as an initial guideline but does not solely determine eligibility for the Intermediate category.\n3) We reserve the right to move players to the Open category if their skill level exceeds their current DUPR rating.\n4) Participants may report players they believe should be in the Open category. We will conduct due diligence, and the final decision will be made by management.\n5) Players who win any tournament, whether on Reclub or elsewhere, will be reviewed to determine their eligibility to compete in the Intermediate category.\n6) No refunds will be given if a player is moved from the Intermediate to the Open category.\n7) Players without a DUPR rating are welcome to participate in the Intermediate tournament, but due diligence will be conducted to assess their eligibility.\n8) If one player is deemed eligible for the Open category while their partner remains in the Intermediate category, the Intermediate player must find a replacement. Otherwise, the entire team will be moved to the Open category.\n9) If, during the tournament, we identify a team that was mistakenly placed in the Intermediate category but should be in the Open category, they may continue playing. However, if they finish in first place, their points will not be counted in the ranking system. They will still receive the prize and medals."
        
        # Create tournament categories with new prize structure
        categories = [
            # Mixed Doubles Open
            TournamentCategory(
                tournament_id=tournament.id,
                category_type=CategoryType.MIXED_DOUBLES,
                name="Mixed Doubles Open",
                max_participants=64,  # 32 teams
                points_awarded=1000,
                format=TournamentFormat.GROUP_KNOCKOUT,
                registration_fee=300.00,  # RM300 per team (RM150 per player)
                prize_percentage=25,  # 25% of total prize pool
                gender_restriction="mixed",
                prize_distribution={"1": 50, "2": 30, "3": 20},
                points_distribution={"1": 100, "2": 70, "3-4": 50, "5-8": 30, "9-16": 15},
                prize_money=3500.00,  # Grand Prize cash amount from Alliance Bank tournament
                has_merchandise=True,
                has_trophies=True,
                prize_summary="Grand Prize: RM3,500 cash + RM1,500 worth of exclusive merchandise\nFirst Runner-Up: RM2,500 cash + RM1,000 worth of exclusive merchandise\nSecond Runner-Up: RM1,500 cash + RM800 worth of exclusive merchandise",
                total_prize_value=9700.00,  # Total of all cash + merchandise
                display_order=10,  # Third in display order
            ),
            
            # Mixed Doubles Intermediate
            TournamentCategory(
                tournament_id=tournament.id,
                category_type=CategoryType.MIXED_DOUBLES,
                name="Mixed Doubles Intermediate",
                max_participants=64,  # 32 teams
                points_awarded=500,
                format=TournamentFormat.GROUP_KNOCKOUT,
                registration_fee=240.00,  # RM240 per team (RM120 per player)
                prize_percentage=15,  # 15% of total prize pool
                gender_restriction="mixed",
                max_dupr_rating=3.5,  # Max DUPR rating for Intermediate
                prize_distribution={"1": 50, "2": 30, "3": 20},
                points_distribution={"1": 100, "2": 70, "3-4": 50, "5-8": 30, "9-16": 15},
                prize_money=1600.00,  # Grand Prize cash amount from Alliance Bank tournament
                has_merchandise=True,
                has_trophies=True,
                description=intermediate_rules,
                prize_summary="Grand Prize: RM1,600 cash + RM1,000 worth of exclusive merchandise\nFirst Runner-Up: RM1,100 cash + RM700 worth of exclusive merchandise\nSecond Runner-Up: RM700 cash + RM300 worth of exclusive merchandise",
                total_prize_value=4400.00,  # Total of all cash + merchandise
                display_order=40,  # Sixth in display order
            ),
            
            # Women's Doubles Open
            TournamentCategory(
                tournament_id=tournament.id,
                category_type=CategoryType.WOMENS_DOUBLES,
                name="Women's Doubles Open",
                max_participants=48,  # 24 teams
                points_awarded=1000,
                format=TournamentFormat.GROUP_KNOCKOUT,
                registration_fee=300.00,  # RM300 per team (RM150 per player)
                prize_percentage=15,  # 15% of total prize pool
                gender_restriction="female",
                prize_distribution={"1": 50, "2": 30, "3": 20},
                points_distribution={"1": 100, "2": 70, "3-4": 50, "5-8": 30, "9-16": 15},
                prize_money=3500.00,  # Grand Prize cash amount from Alliance Bank tournament
                has_merchandise=True,
                has_trophies=True,
                prize_summary="Grand Prize: RM3,500 cash + RM1,500 worth of exclusive merchandise\nFirst Runner-Up: RM2,500 cash + RM1,000 worth of exclusive merchandise\nSecond Runner-Up: RM1,500 cash + RM800 worth of exclusive merchandise",
                total_prize_value=9700.00,  # Total of all cash + merchandise
                display_order=20,  # Second in display order
            ),
            
            # Women's Doubles Intermediate
            TournamentCategory(
                tournament_id=tournament.id,
                category_type=CategoryType.WOMENS_DOUBLES,
                name="Women's Doubles Intermediate",
                max_participants=48,  # 24 teams
                points_awarded=500,
                format=TournamentFormat.GROUP_KNOCKOUT,
                registration_fee=240.00,  # RM240 per team (RM120 per player)
                prize_percentage=10,  # 10% of total prize pool
                gender_restriction="female",
                max_dupr_rating=3.5,  # Max DUPR rating for Intermediate
                prize_distribution={"1": 50, "2": 30, "3": 20},
                points_distribution={"1": 100, "2": 70, "3-4": 50, "5-8": 30, "9-16": 15},
                prize_money=1600.00,  # Grand Prize cash amount from Alliance Bank tournament
                has_merchandise=True,
                has_trophies=True,
                description=intermediate_rules,
                prize_summary="Grand Prize: RM1,600 cash + RM1,000 worth of exclusive merchandise\nFirst Runner-Up: RM1,100 cash + RM700 worth of exclusive merchandise\nSecond Runner-Up: RM700 cash + RM300 worth of exclusive merchandise",
                total_prize_value=4400.00,  # Total of all cash + merchandise
                display_order=50,  # Fifth in display order
            ),
            
            # Men's Doubles Open
            TournamentCategory(
                tournament_id=tournament.id,
                category_type=CategoryType.MENS_DOUBLES,
                name="Men's Doubles Open",
                max_participants=64,  # 32 teams
                points_awarded=1000,
                format=TournamentFormat.GROUP_KNOCKOUT,
                registration_fee=300.00,  # RM300 per team (RM150 per player)
                prize_percentage=25,  # 25% of total prize pool
                gender_restriction="male",
                prize_distribution={"1": 50, "2": 30, "3": 20},
                points_distribution={"1": 100, "2": 70, "3-4": 50, "5-8": 30, "9-16": 15},
                prize_money=3500.00,  # Grand Prize cash amount from Alliance Bank tournament
                has_merchandise=True,
                has_trophies=True,
                prize_summary="Grand Prize: RM3,500 cash + RM1,500 worth of exclusive merchandise\nFirst Runner-Up: RM2,500 cash + RM1,000 worth of exclusive merchandise\nSecond Runner-Up: RM1,500 cash + RM800 worth of exclusive merchandise",
                total_prize_value=9700.00,  # Total of all cash + merchandise
                display_order=1,  # First in display order
            ),
            
            # Men's Doubles Intermediate
            TournamentCategory(
                tournament_id=tournament.id,
                category_type=CategoryType.MENS_DOUBLES,
                name="Men's Doubles Intermediate",
                max_participants=64,  # 32 teams
                points_awarded=500,
                format=TournamentFormat.GROUP_KNOCKOUT,
                registration_fee=240.00,  # RM240 per team (RM120 per player)
                prize_percentage=10,  # 10% of total prize pool
                gender_restriction="male",
                max_dupr_rating=3.5,  # Max DUPR rating for Intermediate
                prize_distribution={"1": 50, "2": 30, "3": 20},
                points_distribution={"1": 100, "2": 70, "3-4": 50, "5-8": 30, "9-16": 15},
                prize_money=1600.00,  # Grand Prize cash amount from Alliance Bank tournament
                has_merchandise=True,
                has_trophies=True,
                description=intermediate_rules,
                prize_summary="Grand Prize: RM1,600 cash + RM1,000 worth of exclusive merchandise\nFirst Runner-Up: RM1,100 cash + RM700 worth of exclusive merchandise\nSecond Runner-Up: RM700 cash + RM300 worth of exclusive merchandise",
                total_prize_value=4400.00,  # Total of all cash + merchandise
                display_order=30,  # Fourth in display order
            ),
        ]
        
        # Add all categories to the database
        for category in categories:
            db.session.add(category)
        
        # Commit to get IDs
        db.session.commit()
        
        # Now add detailed prizes to each category
        
        # For Open Category Doubles (Mixed Doubles Open, Men's Doubles Open, Women's Doubles Open)
        for category in [categories[0], categories[2], categories[4]]:  # Mixed Open, Women's Open, Men's Open
            add_prizes_to_category(category, [
                # Cash prizes exactly as per Alliance Bank tournament
                {"placement": "1", "type": PrizeType.CASH, "amount": 3500.00},    # Grand Prize
                {"placement": "2", "type": PrizeType.CASH, "amount": 2500.00},    # First Runner-Up
                {"placement": "3", "type": PrizeType.CASH, "amount": 750.00},   # Second Runner-Up per team
                
                # Merchandise prizes exactly as per Alliance Bank tournament
                {"placement": "1", "type": PrizeType.MERCHANDISE, "title": "Exclusive Merchandise Package", 
                    "description": "Premium pickleball gear and exclusive Alliance Bank KL Open merchandise", 
                    "value": 1500.00},
                
                {"placement": "2", "type": PrizeType.MERCHANDISE, "title": "Exclusive Merchandise Package", 
                    "description": "High-quality pickleball gear and exclusive Alliance Bank KL Open merchandise", 
                    "value": 1000.00},
                
                {"placement": "3", "type": PrizeType.MERCHANDISE, "title": "Exclusive Merchandise Package", 
                    "description": "Selected pickleball accessories and Alliance Bank KL Open merchandise", 
                    "value": 400.00}
            ])
        
        # For Intermediate Category (Mixed Doubles Intermediate, Men's Doubles Intermediate, Women's Doubles Intermediate)
        for category in [categories[1], categories[3], categories[5]]:  # Mixed Int, Women's Int, Men's Int
            add_prizes_to_category(category, [
                # Cash prizes exactly as per Alliance Bank tournament
                {"placement": "1", "type": PrizeType.CASH, "amount": 1600.00},    # Grand Prize
                {"placement": "2", "type": PrizeType.CASH, "amount": 1100.00},    # First Runner-Up
                {"placement": "3", "type": PrizeType.CASH, "amount": 350.00},   # Second Runner-Up per team
                
                # Merchandise prizes exactly as per Alliance Bank tournament
                {"placement": "1", "type": PrizeType.MERCHANDISE, "title": "Exclusive Merchandise Package", 
                    "description": "Quality pickleball gear and exclusive Alliance Bank KL Open merchandise", 
                    "value": 1000.00},
                
                {"placement": "2", "type": PrizeType.MERCHANDISE, "title": "Exclusive Merchandise Package", 
                    "description": "Selected pickleball gear and Alliance Bank KL Open merchandise", 
                    "value": 700.00},
                
                {"placement": "3", "type": PrizeType.MERCHANDISE, "title": "Exclusive Merchandise Package", 
                    "description": "Alliance Bank KL Open branded merchandise and accessories", 
                    "value": 150.00}
            ])
        
        # Commit all changes
        db.session.commit()
        
        print("Tournament seeded successfully with detailed prize structure!")
    else:
        print("Tournament already exists, updating status to ONGOING...")
    
    # Update tournament status to ONGOING
    tournament.status = TournamentStatus.ONGOING
    db.session.commit()
    
    return tournament

def add_prizes_to_category(category, prizes):
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

def generate_payment_reference(tournament):
    """Generate a unique payment reference"""
    prefix = tournament.payment_reference_prefix or "REF"
    random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"{prefix}{random_suffix}"

def create_player_profile(name, country="Malaysia", dupr_rating=None):
    """Helper function to create a Player user and profile"""
    username = name.lower().replace(" ", ".")
    email = f"{username}@example.com"
    
    # Create user if it doesn't exist
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(
            username=username,
            email=email,
            full_name=name,
            role=UserRole.PLAYER,
            is_active=True
        )
        user.set_password("password")
        db.session.add(user)
        db.session.flush()
        
        # Create profile
        profile = user.player_profile
        if not profile:
            profile = user.player_profile = PlayerProfile(
                user_id=user.id,
                full_name=name,
                country=country,
                city="Kuala Lumpur" if country == "Malaysia" else "Unknown",
                age=random.randint(25, 45),
                bio=f"Professional pickleball player from {country}.",
                plays="Right-handed" if random.random() > 0.2 else "Left-handed",
                height=f"{5 + random.randint(0, 10) // 12}'{random.randint(0, 11)}\"",
                paddle="ProKennex Pro Flight",
                coach_academy="Elite Pickleball Academy",
                turned_pro=2020 + random.randint(0, 3),
                # Social media links
                instagram=f"https://instagram.com/{username}",
                facebook=f"https://facebook.com/{username}",
                twitter=f"https://twitter.com/{username}",
                tiktok=f"https://tiktok.com/@{username}",
                xiaohongshu=f"https://xiaohongshu.com/{username}",
                # Stats
                matches_won=random.randint(10, 50),
                matches_lost=random.randint(5, 30),
                avg_match_duration=random.randint(30, 75)
            )
            db.session.add(profile)
        
        db.session.commit()
    
    return user

def seed_mens_doubles():
    """Seed Men's Doubles Open with 16 teams and group stage + knockout bracket"""
    tournament = Tournament.query.filter_by(name="SportsSync-Oncourt Pickleball Tournament").first()
    if not tournament:
        print("Tournament not found. Please run seed_tournament() first.")
        return
    
    # Find the Men's Doubles Open category
    category = TournamentCategory.query.filter_by(
        tournament_id=tournament.id,
        name="Men's Doubles Open"
    ).first()
    
    if not category:
        print("Men's Doubles Open category not found.")
        return
    
    # Check if we already have teams/registrations
    existing_registrations = Registration.query.filter_by(category_id=category.id).count()
    if existing_registrations > 0:
        print(f"Already have {existing_registrations} registrations for Men's Doubles. Clearing existing data...")
        
        # Delete existing matches, groups, teams, and registrations
        Match.query.filter_by(category_id=category.id).delete()
        GroupStanding.query.join(Group).filter(Group.category_id == category.id).delete()
        Group.query.filter_by(category_id=category.id).delete()
        Team.query.filter_by(category_id=category.id).delete()
        Registration.query.filter_by(category_id=category.id).delete()
        db.session.commit()
    
    # Create 16 teams (32 players)
    team_data = [
        # Team 1 (Seed 1)
        {"p1": "John Smith", "p2": "Michael Wong", "country": "Malaysia", "seed": 1, "dupr": 5.5},
        # Team 2 (Seed 2)
        {"p1": "David Lee", "p2": "Richard Tan", "country": "Singapore", "seed": 2, "dupr": 5.4},
        # Team 3 (Seed 3)
        {"p1": "Thomas Chen", "p2": "William Zhang", "country": "Taiwan", "seed": 3, "dupr": 5.3},
        # Team 4 (Seed 4)
        {"p1": "James Lim", "p2": "Robert Ng", "country": "Malaysia", "seed": 4, "dupr": 5.2},
        # Team 5 (Seed 5-8)
        {"p1": "Daniel Chong", "p2": "Kevin Yap", "country": "Malaysia", "seed": 5, "dupr": 5.1},
        # Team 6 (Seed 5-8)
        {"p1": "Joseph Tan", "p2": "Charles Kim", "country": "South Korea", "seed": 6, "dupr": 5.0},
        # Team 7 (Seed 5-8)
        {"p1": "Edward Wu", "p2": "Steven Zhou", "country": "China", "seed": 7, "dupr": 4.9},
        # Team 8 (Seed 5-8)
        {"p1": "Kenneth Park", "p2": "George Huang", "country": "Taiwan", "seed": 8, "dupr": 4.8},
        # Teams 9-16 (Unseeded)
        {"p1": "Ryan Tan", "p2": "Jason Lee", "country": "Malaysia", "seed": None, "dupr": 4.7},
        {"p1": "Peter Wang", "p2": "Eric Liu", "country": "China", "seed": None, "dupr": 4.6},
        {"p1": "Frank Kim", "p2": "Victor Kang", "country": "South Korea", "seed": None, "dupr": 4.5},
        {"p1": "Henry Lau", "p2": "Timothy Goh", "country": "Singapore", "seed": None, "dupr": 4.4},
        {"p1": "Alex Yeo", "p2": "Brian Tan", "country": "Malaysia", "seed": None, "dupr": 4.3},
        {"p1": "Oscar Chan", "p2": "Nathan Lim", "country": "Malaysia", "seed": None, "dupr": 4.2},
        {"p1": "Patrick Wong", "p2": "Quentin Cheung", "country": "Hong Kong", "seed": None, "dupr": 4.1},
        {"p1": "Samuel Chiu", "p2": "Umar Teo", "country": "Indonesia", "seed": None, "dupr": 4.0}
    ]
    
    team_registrations = []
    team_objects = []
    
    # Register all teams
    for idx, team in enumerate(team_data):
        player1 = create_player_profile(team["p1"], team["country"], team["dupr"])
        player2 = create_player_profile(team["p2"], team["country"], team["dupr"])
        
        # Create registration
        registration = Registration(
            category_id=category.id,
            registration_date=datetime.utcnow() - timedelta(days=random.randint(5, 30)),
            registration_fee=category.registration_fee,
            
            # Flag this as a team registration
            is_team_registration=True,
            
            # Payment info
            payment_status='approved',
            payment_verified=True,
            payment_verified_at=datetime.utcnow() - timedelta(days=random.randint(2, 10)),
            payment_proof=f"payment_{idx+1}.png",
            payment_proof_uploaded_at=datetime.utcnow() - timedelta(days=random.randint(3, 20)),
            payment_reference=generate_payment_reference(tournament),
            
            # Player 1 details
            player_id=player1.player_profile.id,
            player1_name=player1.full_name,
            player1_email=player1.email,
            player1_phone="+601" + ''.join(random.choices(string.digits, k=9)),
            player1_dupr_id="MN" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4)),
            player1_dupr_rating=team["dupr"],
            player1_date_of_birth=date(random.randint(1980, 2000), random.randint(1, 12), random.randint(1, 28)),
            player1_nationality=team["country"],
            
            # Player 2 details
            partner_id=player2.player_profile.id,
            player2_name=player2.full_name,
            player2_email=player2.email,
            player2_phone="+601" + ''.join(random.choices(string.digits, k=9)),
            player2_dupr_id="MN" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4)),
            player2_dupr_rating=team["dupr"] - random.uniform(0.1, 0.3),  # Slightly lower rating
            player2_date_of_birth=date(random.randint(1980, 2000), random.randint(1, 12), random.randint(1, 28)),
            player2_nationality=team["country"],
            
            # Team seed
            seed=team["seed"],
            
            # Agreements
            terms_agreement=True,
            liability_waiver=True,
            media_release=True,
            pdpa_consent=True,
        )
        
        team_registrations.append(registration)
        db.session.add(registration)
    
    db.session.commit()
    
    # Create teams from registrations
    for registration in team_registrations:
        team = Team(
            player1_id=registration.player_id,
            player2_id=registration.partner_id,
            category_id=category.id
        )
        team_objects.append(team)
        db.session.add(team)
    
    db.session.commit()
    
    # Create 4 groups with 4 teams each
    group_names = ["A", "B", "C", "D"]
    groups = []
    
    for i, name in enumerate(group_names):
        group = Group(
            category_id=category.id,
            name=f"Group {name}"
        )
        groups.append(group)
        db.session.add(group)
    
    db.session.commit()
    
    # Distribute teams to groups based on seeding
    # Group A: Seed 1, Seed 8, Unseeded 9, Unseeded 16
    # Group B: Seed 2, Seed 7, Unseeded 10, Unseeded 15
    # Group C: Seed 3, Seed 6, Unseeded 11, Unseeded 14
    # Group D: Seed 4, Seed 5, Unseeded 12, Unseeded 13
    group_distribution = [
        [0, 7, 8, 15],   # Group A: 1, 8, 9, 16
        [1, 6, 9, 14],   # Group B: 2, 7, 10, 15
        [2, 5, 10, 13],  # Group C: 3, 6, 11, 14
        [3, 4, 11, 12]   # Group D: 4, 5, 12, 13
    ]
    
    # Add teams to groups and create standings
    for g_idx, team_indices in enumerate(group_distribution):
        for t_idx in team_indices:
            team = team_objects[t_idx]
            
            # Create standing
            standing = GroupStanding(
                group_id=groups[g_idx].id,
                team_id=team.id,
                matches_played=0,
                matches_won=0,
                matches_lost=0,
                sets_won=0,
                sets_lost=0,
                points_won=0,
                points_lost=0,
                position=None  # Will be calculated later
            )
            db.session.add(standing)
    
    db.session.commit()
    
    # Create group stage matches
    for g_idx, group in enumerate(groups):
        team_indices = group_distribution[g_idx]
        group_teams = [team_objects[idx] for idx in team_indices]
        
        # Create round-robin matches (each team plays every other team)
        match_number = 1
        for i in range(len(group_teams)):
            for j in range(i + 1, len(group_teams)):
                team1 = group_teams[i]
                team2 = group_teams[j]
                
                # Randomize match results (80% complete, 20% pending)
                completed = random.random() < 0.8
                
                match = Match(
                    category_id=category.id,
                    group_id=group.id,
                    round=match_number,
                    match_order=match_number,
                    team1_id=team1.id,
                    team2_id=team2.id,
                    completed=completed,
                    court=f"Court {random.randint(1, 8)}",
                    scheduled_time=datetime.utcnow() + timedelta(hours=random.randint(-24, 24)),
                    referee_verified=completed,
                    player_verified=completed if random.random() < 0.7 else False,
                    livestream_url=f"https://youtube.com/watch?v=pickleball{random.randint(1, 1000)}" if random.random() < 0.3 else None
                )
                
                if completed:
                    # Determine winner randomly but favor higher seeds
                    seed_diff = (team_indices[i] if team_indices[i] is not None else 16) - (team_indices[j] if team_indices[j] is not None else 16)
                    higher_seed_advantage = 0.5 + min(0.4, abs(seed_diff) * 0.05) * (1 if seed_diff < 0 else -1)
                    
                    team1_wins = random.random() < higher_seed_advantage
                    
                    if team1_wins:
                        match.winning_team_id = team1.id
                        match.losing_team_id = team2.id
                    else:
                        match.winning_team_id = team2.id
                        match.losing_team_id = team1.id
                    
                    # Create score (realistic for pickleball)
                    score = MatchScore(
                        match_id=match.id,
                        set_number=1
                    )
                    
                    if team1_wins:
                        score.player1_score = 11
                        score.player2_score = random.randint(5, 9)
                    else:
                        score.player1_score = random.randint(5, 9)
                        score.player2_score = 11
                    
                    db.session.add(score)
                    
                    # Update standings
                    standings = GroupStanding.query.filter(
                        (GroupStanding.group_id == group.id) & 
                        ((GroupStanding.team_id == team1.id) | (GroupStanding.team_id == team2.id))
                    ).all()
                    
                    for standing in standings:
                        if standing.team_id == match.winning_team_id:
                            standing.matches_played += 1
                            standing.matches_won += 1
                            standing.sets_won += 1
                            if team1_wins:
                                standing.points_won += score.player1_score
                                standing.points_lost += score.player2_score
                            else:
                                standing.points_won += score.player2_score
                                standing.points_lost += score.player1_score
                        else:
                            standing.matches_played += 1
                            standing.matches_lost += 1
                            standing.sets_lost += 1
                            if team1_wins:
                                standing.points_won += score.player2_score
                                standing.points_lost += score.player1_score
                            else:
                                standing.points_won += score.player1_score
                                standing.points_lost += score.player2_score
                
                db.session.add(match)
                match_number += 1
    
    db.session.commit()
    
    # Calculate standings positions
    for group in groups:
        standings = GroupStanding.query.filter_by(group_id=group.id).all()
        
        # Sort by:
        # 1. Matches won (descending)
        # 2. Set difference (sets_won - sets_lost) (descending)
        # 3. Point difference (points_won - points_lost) (descending)
        standings.sort(key=lambda s: (
            -s.matches_won, 
            -(s.sets_won - s.sets_lost), 
            -(s.points_won - s.points_lost)
        ))
        
        # Assign positions
        for idx, standing in enumerate(standings):
            standing.position = idx + 1
    
    db.session.commit()
    
    # Create knockout stage matches (top 2 teams from each group advance)
    # Quarterfinals:
    # QF1: Group A 1st vs Group C 2nd
    # QF2: Group B 1st vs Group D 2nd
    # QF3: Group C 1st vs Group A 2nd
    # QF4: Group D 1st vs Group B 2nd
    
    # Get qualified teams (top 2 from each group)
    qualified_teams = []
    for group in groups:
        group_qualifiers = (
            db.session.query(GroupStanding.team_id)
            .filter(GroupStanding.group_id == group.id, GroupStanding.position <= 2)
            .order_by(GroupStanding.position)
            .all()
        )
        qualified_teams.append([team_id for team_id, in group_qualifiers])
    
    # Create quarterfinal matches
    qf_matchups = [
        (qualified_teams[0][0], qualified_teams[3][1]),  # Group A 1st vs Group D 2nd
        (qualified_teams[1][0], qualified_teams[2][1]),  # Group B 1st vs Group C 2nd
        (qualified_teams[2][0], qualified_teams[1][1]),  # Group C 1st vs Group B 2nd
        (qualified_teams[3][0], qualified_teams[0][1])   # Group D 1st vs Group A 2nd
    ]
    
    qf_matches = []
    for idx, (team1_id, team2_id) in enumerate(qf_matchups):
        # Determine if the match is completed (75% chance)
        completed = random.random() < 0.75
        
        match = Match(
            category_id=category.id,
            round=4,  # Quarterfinals (round numbers count backward from final, with 1 being final)
            match_order=idx + 1,
            team1_id=team1_id,
            team2_id=team2_id,
            completed=completed,
            court=f"Court {random.randint(1, 4)}",
            scheduled_time=datetime.utcnow() + timedelta(hours=random.randint(8, 16)),
            referee_verified=completed,
            player_verified=completed if random.random() < 0.7 else False,
            livestream_url=f"https://youtube.com/watch?v=pickleball{random.randint(1000, 2000)}" if random.random() < 0.5 else None
        )
        
        if completed:
            # Determine winner randomly
            team1_wins = random.random() < 0.5
            
            if team1_wins:
                match.winning_team_id = team1_id
                match.losing_team_id = team2_id
            else:
                match.winning_team_id = team2_id
                match.losing_team_id = team1_id
            
            # Create score
            score = MatchScore(
                match_id=match.id,
                set_number=1
            )
            
            if team1_wins:
                score.player1_score = 11
                score.player2_score = random.randint(5, 9)
            else:
                score.player1_score = random.randint(5, 9)
                score.player2_score = 11
            
            db.session.add(score)
        
        db.session.add(match)
        qf_matches.append(match)
    
    db.session.commit()
    
    # Create semifinal matches (not completed yet - we want these to be pending)
    sf_matchups = [
        (qf_matches[0], qf_matches[1]),  # QF1 winner vs QF2 winner
        (qf_matches[2], qf_matches[3])   # QF3 winner vs QF4 winner
    ]
    
    for idx, (qf1, qf2) in enumerate(sf_matchups):
        # Only create semifinal if both quarterfinals are completed
        if qf1.completed and qf2.completed:
            match = Match(
                category_id=category.id,
                round=2,  # Semifinals
                match_order=idx + 1,
                team1_id=qf1.winning_team_id,
                team2_id=qf2.winning_team_id,
                completed=False,  # Not completed yet
                court=f"Court {random.randint(1, 2)}",
                scheduled_time=datetime.utcnow() + timedelta(hours=random.randint(20, 28)),
                referee_verified=False,
                player_verified=False
            )
            db.session.add(match)
    
    db.session.commit()
    
    print("Men's Doubles Open category seeded with 16 teams in 4 groups and knockout stage!")


def seed_womens_doubles():
    """Seed Women's Doubles Open with 16 teams but no bracket generated yet"""
    tournament = Tournament.query.filter_by(name="SportsSync-Oncourt Pickleball Tournament").first()
    if not tournament:
        print("Tournament not found. Please run seed_tournament() first.")
        return
    
    # Find the Women's Doubles Open category
    category = TournamentCategory.query.filter_by(
        tournament_id=tournament.id,
        name="Women's Doubles Open"
    ).first()
    
    if not category:
        print("Women's Doubles Open category not found.")
        return
    
    # Check if we already have teams/registrations
    existing_registrations = Registration.query.filter_by(category_id=category.id).count()
    if existing_registrations > 0:
        print(f"Already have {existing_registrations} registrations for Women's Doubles. Clearing existing data...")
        
        # Delete existing teams and registrations
        Match.query.filter_by(category_id=category.id).delete()
        GroupStanding.query.join(Group).filter(Group.category_id == category.id).delete()
        Group.query.filter_by(category_id=category.id).delete()
        Team.query.filter_by(category_id=category.id).delete()
        Registration.query.filter_by(category_id=category.id).delete()
        db.session.commit()
    
    # Create 16 teams (32 players)
    team_data = [
        # Team 1 (Seed 1)
        {"p1": "Alice Johnson", "p2": "Emma Davis", "country": "USA", "seed": 1, "dupr": 5.3},
        # Team 2 (Seed 2)
        {"p1": "Sophia Chen", "p2": "Olivia Wang", "country": "Taiwan", "seed": 2, "dupr": 5.2},
        # Team 3 (Seed 3)
        {"p1": "Isabella Kim", "p2": "Mia Park", "country": "South Korea", "seed": 3, "dupr": 5.1},
        # Team 4 (Seed 4)
        {"p1": "Amelia Tan", "p2": "Charlotte Ng", "country": "Malaysia", "seed": 4, "dupr": 5.0},
        # Team 5 (Seed 5-8)
        {"p1": "Harper Lee", "p2": "Abigail Lim", "country": "Singapore", "seed": 5, "dupr": 4.9},
        # Team 6 (Seed 5-8)
        {"p1": "Emily Zhang", "p2": "Elizabeth Wu", "country": "China", "seed": 6, "dupr": 4.8},
        # Team 7 (Seed 5-8)
        {"p1": "Avery Wong", "p2": "Sofia Cheung", "country": "Hong Kong", "seed": 7, "dupr": 4.7},
        # Team 8 (Seed 5-8)
        {"p1": "Scarlett Yeo", "p2": "Victoria Lin", "country": "Malaysia", "seed": 8, "dupr": 4.6},
        # Teams 9-16 (Unseeded)
        {"p1": "Grace Lai", "p2": "Chloe Hsu", "country": "Taiwan", "seed": None, "dupr": 4.5},
        {"p1": "Lily Yuan", "p2": "Hannah Zhao", "country": "China", "seed": None, "dupr": 4.4},
        {"p1": "Zoe Kang", "p2": "Madison Ahn", "country": "South Korea", "seed": None, "dupr": 4.3},
        {"p1": "Layla Teo", "p2": "Penelope Goh", "country": "Singapore", "seed": None, "dupr": 4.2},
        {"p1": "Nora Abdullah", "p2": "Riley Hashim", "country": "Malaysia", "seed": None, "dupr": 4.1},
        {"p1": "Stella Liew", "p2": "Luna Chang", "country": "Taiwan", "seed": None, "dupr": 4.0},
        {"p1": "Hazel Fong", "p2": "Violet Teoh", "country": "Malaysia", "seed": None, "dupr": 3.9},
        {"p1": "Lucy Kwok", "p2": "Audrey Chia", "country": "Singapore", "seed": None, "dupr": 3.8}
    ]
    
    team_registrations = []
    
    # Register all teams
    for idx, team in enumerate(team_data):
        player1 = create_player_profile(team["p1"], team["country"], team["dupr"])
        player2 = create_player_profile(team["p2"], team["country"], team["dupr"])
        
        # Create registration
        registration = Registration(
            category_id=category.id,
            registration_date=datetime.utcnow() - timedelta(days=random.randint(5, 30)),
            registration_fee=category.registration_fee,
            
            # Flag this as a team registration
            is_team_registration=True,
            
            # Payment info
            payment_status='approved',
            payment_verified=True,
            payment_verified_at=datetime.utcnow() - timedelta(days=random.randint(2, 10)),
            payment_proof=f"payment_w_{idx+1}.png",
            payment_proof_uploaded_at=datetime.utcnow() - timedelta(days=random.randint(3, 20)),
            payment_reference=generate_payment_reference(tournament),
            
            # Player 1 details
            player_id=player1.player_profile.id,
            player1_name=player1.full_name,
            player1_email=player1.email,
            player1_phone="+601" + ''.join(random.choices(string.digits, k=9)),
            player1_dupr_id="WN" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4)),
            player1_dupr_rating=team["dupr"],
            player1_date_of_birth=date(random.randint(1980, 2000), random.randint(1, 12), random.randint(1, 28)),
            player1_nationality=team["country"],
            
            # Player 2 details
            partner_id=player2.player_profile.id,
            player2_name=player2.full_name,
            player2_email=player2.email,
            player2_phone="+601" + ''.join(random.choices(string.digits, k=9)),
            player2_dupr_id="WN" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4)),
            player2_dupr_rating=team["dupr"] - random.uniform(0.1, 0.3),  # Slightly lower rating
            player2_date_of_birth=date(random.randint(1980, 2000), random.randint(1, 12), random.randint(1, 28)),
            player2_nationality=team["country"],
            
            # Team seed
            seed=team["seed"],
            
            # Agreements
            terms_agreement=True,
            liability_waiver=True,
            media_release=True,
            pdpa_consent=True,
        )
        
        team_registrations.append(registration)
        db.session.add(registration)
    
    db.session.commit()
    
    print("Women's Doubles Open category seeded with 16 teams (registrations only, no bracket generated)!")


def main():
    """Main function to seed the database"""
    # Reset database
    if len(sys.argv) > 1 and sys.argv[1] == '--reset':
        print("Dropping all tables...")
        db.drop_all()
        print("Creating all tables...")
        db.create_all()
    
    # Seed tournament and update to ONGOING status
    tournament = seed_tournament()
    
    # Seed Men's Doubles Open with 16 teams in 4 groups + knockout stage
    seed_mens_doubles()
    
    # Seed Women's Doubles Open with 16 teams (no bracket generation)
    seed_womens_doubles()
    
    print(f"Seeding complete! Tournament status is now: {tournament.status.name}")
    print("Men's Doubles: 16 teams in 4 groups, with top 2 from each group in knockout stage up to semifinals")
    print("Women's Doubles: 16 teams registered but bracket not generated yet")

if __name__ == "__main__":
    with app.app_context():
        main()