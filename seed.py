from datetime import datetime, timedelta
from app import db, create_app
import sys
from app.models import Tournament, TournamentCategory, CategoryType, TournamentTier, TournamentFormat, TournamentStatus, Venue, User, UserRole, PrizeType, Prize

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
        status=TournamentStatus.UPCOMING,
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
                "value": 400.00},  
            
            # Trophies
            {"placement": "1", "type": PrizeType.TROPHY, "title": "Grand Prize Trophy"},
            {"placement": "2", "type": PrizeType.TROPHY, "title": "First Runner-Up Trophy"},
            {"placement": "3", "type": PrizeType.MEDAL, "title": "Second Runner-Up Medal"}
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
                "value": 150.00},  
            
            # Trophies
            {"placement": "1", "type": PrizeType.TROPHY, "title": "Grand Prize Trophy"},
            {"placement": "2", "type": PrizeType.TROPHY, "title": "First Runner-Up Trophy"},
            {"placement": "3", "type": PrizeType.MEDAL, "title": "Second Runner-Up Medal"}
        ])
    
    # Commit all changes
    db.session.commit()
    
    print("Tournament seeded successfully with detailed prize structure!")

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
        elif prize_type in [PrizeType.MERCHANDISE, PrizeType.VOUCHER, PrizeType.SPONSORED_PRODUCT]:
            prize.title = prize_data["title"]
            prize.description = prize_data.get("description")
            prize.monetary_value = prize_data.get("value", 0.0)
            prize.quantity = prize_data.get("quantity", 1)
            if "vendor" in prize_data:
                prize.vendor = prize_data["vendor"]
            if "expiry_date" in prize_data:
                prize.expiry_date = prize_data["expiry_date"]
        elif prize_type in [PrizeType.TROPHY, PrizeType.MEDAL]:
            prize.title = prize_data["title"]
            prize.quantity = prize_data.get("quantity", 1)
            # Most trophies don't have a monetary value in the model
        
        db.session.add(prize)


def main():
    """Main function to seed the database"""
    # Reset database
    if len(sys.argv) > 1 and sys.argv[1] == '--reset':
        print("Dropping all tables...")
        db.drop_all()
        print("Creating all tables...")
        db.create_all()
    
    seed_tournament()

if __name__ == "__main__":
    with app.app_context():
        main()