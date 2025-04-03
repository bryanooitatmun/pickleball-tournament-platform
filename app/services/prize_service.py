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
        Calculate prize money for each category based on its prizes,
        and update the tournament totals
        """
        tournament = Tournament.query.get_or_404(tournament_id)
        categories = TournamentCategory.query.filter_by(tournament_id=tournament_id).all()
        
        # First, calculate prize money for each category based on its prizes
        for category in categories:
            category.calculate_prize_values()
        
        # Then, update the tournament totals
        tournament.total_cash_prize = sum(cat.prize_money or 0.0 for cat in categories)
        tournament.total_prize_value = sum(cat.total_prize_value or 0.0 for cat in categories)
        
        db.session.commit()
        return categories
