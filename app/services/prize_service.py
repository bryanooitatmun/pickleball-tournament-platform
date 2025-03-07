from app import db
from app.models import Tournament, TournamentCategory, Match, MatchScore, Group, GroupStanding
from app.models import Team, Registration, MatchStage, CategoryType
from sqlalchemy import func
from collections import defaultdict

class PrizeService:
    """Service for managing prize money distribution"""
    
    @staticmethod
    def distribute_prize_pool(tournament_id):
        """
        Distribute total prize pool among categories and calculate
        prize money for each placement
        """
        tournament = Tournament.query.get_or_404(tournament_id)
        categories = TournamentCategory.query.filter_by(tournament_id=tournament_id).all()
        
        # Validate that category percentages add up to 100%
        total_percentage = sum(cat.prize_percentage for cat in categories)
        if total_percentage != 100:
            # Normalize if not exactly 100%
            adjustment_factor = 100 / total_percentage
            for category in categories:
                category.prize_percentage *= adjustment_factor
        
        # Calculate prize money for each category
        for category in categories:
            category.calculate_prize_money(tournament.prize_pool)
        
        db.session.commit()
        return categories
