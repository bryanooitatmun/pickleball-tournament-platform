from app import db
from app.models import Tournament, TournamentCategory, Match, MatchScore, Group, GroupStanding
from app.models import PlayerProfile, Team, Registration, MatchStage, CategoryType
from sqlalchemy import func
from collections import defaultdict

class RegistrationService:
    """Service for tournament registration with DUPR rating validation"""
    
    @staticmethod
    def validate_registration(player_id, category_id, partner_id=None):
        """
        Validate if a player/team can register for a category based on restrictions
        Returns (is_valid, error_message)
        """
        category = TournamentCategory.query.get_or_404(category_id)
        player = PlayerProfile.query.get_or_404(player_id)
        
        # Check if category is full
        registrations_count = Registration.query.filter_by(category_id=category_id).count()
        if registrations_count >= category.max_participants:
            return False, "This category is already full."
        
        # Check gender restrictions
        if category.gender_restriction:
            if category.gender_restriction != player.gender:
                return False, f"This category is restricted to {category.gender_restriction} players."
        
        # Check age restrictions
        if category.min_age and player.age < category.min_age:
            return False, f"Player must be at least {category.min_age} years old."
        
        if category.max_age and player.age > category.max_age:
            return False, f"Player must be under {category.max_age} years old."
        
        # Check DUPR rating restrictions for appropriate category
        category_type = category.category_type
        if category_type == CategoryType.MENS_SINGLES:
            player_rating = player.mens_singles_dupr
        elif category_type == CategoryType.WOMENS_SINGLES:
            player_rating = player.womens_singles_dupr
        elif category_type == CategoryType.MENS_DOUBLES:
            player_rating = player.mens_doubles_dupr
        elif category_type == CategoryType.WOMENS_DOUBLES:
            player_rating = player.womens_doubles_dupr
        elif category_type == CategoryType.MIXED_DOUBLES:
            player_rating = player.mixed_doubles_dupr
        else:
            player_rating = None
        
        if category.min_dupr_rating and (not player_rating or player_rating < category.min_dupr_rating):
            return False, f"Minimum DUPR rating of {category.min_dupr_rating} required."
        
        if category.max_dupr_rating and (player_rating and player_rating > category.max_dupr_rating):
            return False, f"Maximum DUPR rating of {category.max_dupr_rating} allowed."
        
        # For doubles, check partner
        if category.is_doubles():
            if not partner_id:
                return False, "Partner required for doubles events."
            
            partner = Player.query.get_or_404(partner_id)
            
            # Check partner gender restrictions for mixed doubles
            if category_type == CategoryType.MIXED_DOUBLES:
                if player.gender == partner.gender:
                    return False, "Mixed doubles requires partners of different genders."
            
            # Check partner age restrictions
            if category.min_age and partner.age < category.min_age:
                return False, f"Partner must be at least {category.min_age} years old."
            
            if category.max_age and partner.age > category.max_age:
                return False, f"Partner must be under {category.max_age} years old."
            
            # Check partner DUPR rating
            if category_type == CategoryType.MENS_DOUBLES:
                partner_rating = partner.mens_doubles_dupr
            elif category_type == CategoryType.WOMENS_DOUBLES:
                partner_rating = partner.womens_doubles_dupr
            elif category_type == CategoryType.MIXED_DOUBLES:
                partner_rating = partner.mixed_doubles_dupr
            else:
                partner_rating = None
            
            if category.min_dupr_rating and (not partner_rating or partner_rating < category.min_dupr_rating):
                return False, f"Partner's minimum DUPR rating of {category.min_dupr_rating} required."
            
            if category.max_dupr_rating and (partner_rating and partner_rating > category.max_dupr_rating):
                return False, f"Partner's maximum DUPR rating of {category.max_dupr_rating} allowed."
        
        return True, None