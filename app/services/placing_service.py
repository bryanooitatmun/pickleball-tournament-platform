from app import db
from app.models import TournamentCategory, Match, MatchStage, TournamentStatus
from collections import defaultdict

class PlacingService:
    """Service for determining tournament placings and distributing prizes/points"""
    
    @staticmethod
    def get_placings(category_id):
        """
        Get complete placings for a category
        Returns a list of placements with player/team, place, points earned, prize earned
        """
        category = TournamentCategory.query.get_or_404(category_id)
        
        # Ensure category is completed
        incomplete_matches = Match.query.filter_by(category_id=category_id, completed=False).count()
        if incomplete_matches > 0:
            return []
        
        placings = []
        
        # Get all knockout stage matches for this category
        knockout_matches = []
        
        # Check if Match model has stage field
        if hasattr(Match, 'stage'):
            knockout_matches = Match.query.filter_by(
                category_id=category_id,
                stage=MatchStage.KNOCKOUT
            ).all()

            third_place_match = Match.query.filter_by(
                category_id=category_id,
                stage=MatchStage.PLAYOFF
            ).all()

            knockout_matches = knockout_matches + third_place_match
        else:
            # Fallback: assume matches without group_id are knockout matches
            knockout_matches = Match.query.filter_by(
                category_id=category_id
            ).filter(Match.group_id.is_(None)).all()
        
        # Process the matches by round
        matches_by_round = defaultdict(list)
        for match in knockout_matches:
            matches_by_round[match.round].append(match)
        
        # Calculate placings from matches
        PlacingService._add_final_placings(placings, matches_by_round, category.is_doubles())
        PlacingService._add_semifinal_placings(placings, matches_by_round, category.is_doubles())
        PlacingService._add_quarterfinal_placings(placings, matches_by_round, category.is_doubles())
        PlacingService._add_remaining_placings(placings, matches_by_round, category.is_doubles())
        
        # Add points and prize money for each placement
        for placing in placings:
            place = placing['place']
            
            # Calculate points based on category and place
            points = PlacingService._calculate_points(category, place)
            placing['points'] = points
            
            # Calculate prize money based on category and place
            prize = PlacingService._calculate_prize(category, place)
            placing['prize'] = prize
        return placings
    
    @staticmethod
    def _add_final_placings(placings, matches_by_round, is_doubles):
        """Add 1st and 2nd place from the final"""
        if 1 in matches_by_round and matches_by_round[1]:
            final = matches_by_round[1][0]
            
            # Add winner (1st place)
            if is_doubles:
                if hasattr(final, 'winning_team_id') and final.winning_team_id:
                    placings.append({
                        'place': 1,
                        'participant': final.winner,
                        'is_team': True
                    })
            else:
                if hasattr(final, 'winning_player_id') and final.winning_player_id:
                    placings.append({
                        'place': 1,
                        'participant': final.winner,
                        'is_team': False
                    })
            
            # Add runner-up (2nd place)
            if is_doubles:
                if hasattr(final, 'losing_team_id') and final.losing_team_id:
                    placings.append({
                        'place': 2,
                        'participant': final.loser,
                        'is_team': True
                    })
            else:
                if hasattr(final, 'losing_player_id') and final.losing_player_id:
                    placings.append({
                        'place': 2,
                        'participant': final.loser,
                        'is_team': False
                    })
    
    @staticmethod
    def _add_semifinal_placings(placings, matches_by_round, is_doubles):
        """Add 3rd and 4th place from semifinals"""
        # Check if there's a 3rd place playoff match
        third_place_match = None
        for match in matches_by_round.get(1.5, []):
            if hasattr(match, 'stage') and match.stage == MatchStage.PLAYOFF:
                third_place_match = match
                break
        
        if third_place_match:
            # Add 3rd place from playoff match winner
            if is_doubles:
                if hasattr(third_place_match, 'winning_team_id') and third_place_match.winning_team_id:
                    placings.append({
                        'place': 3,
                        'participant': third_place_match.winner,
                        'is_team': True
                    })
            else:
                if hasattr(third_place_match, 'winning_player_id') and third_place_match.winning_player_id:
                    placings.append({
                        'place': 3,
                        'participant': third_place_match.winner,
                        'is_team': False
                    })
            
            # Add 4th place from playoff match loser
            if is_doubles:
                if hasattr(third_place_match, 'losing_team_id') and third_place_match.losing_team_id:
                    placings.append({
                        'place': 4,
                        'participant': third_place_match.loser,
                        'is_team': True
                    })
            else:
                if hasattr(third_place_match, 'losing_player_id') and third_place_match.losing_player_id:
                    placings.append({
                        'place': 4,
                        'participant': third_place_match.loser,
                        'is_team': False
                    })
        elif 2 in matches_by_round:
            # If no playoff match, both semifinal losers get 3rd place
            semifinal_losers = []
            
            for match in matches_by_round[2]:
                if is_doubles:
                    if hasattr(match, 'losing_team_id') and match.losing_team_id:
                        semifinal_losers.append({
                            'place': 3,  # Tied for 3rd
                            'participant': match.loser,
                            'is_team': True
                        })
                else:
                    if hasattr(match, 'losing_player_id') and match.losing_player_id:
                        semifinal_losers.append({
                            'place': 3,  # Tied for 3rd
                            'participant': match.loser,
                            'is_team': False
                        })
            
            placings.extend(semifinal_losers)
    
    @staticmethod
    def _add_quarterfinal_placings(placings, matches_by_round, is_doubles):
        """Add 5th-8th places from quarterfinals"""
        if 3 in matches_by_round:
            quarterfinal_losers = []
            
            for match in matches_by_round[3]:
                if is_doubles:
                    if hasattr(match, 'losing_team_id') and match.losing_team_id:
                        quarterfinal_losers.append({
                            'place': 5,  # Tied for 5th
                            'participant': match.loser,
                            'is_team': True
                        })
                else:
                    if hasattr(match, 'losing_player_id') and match.losing_player_id:
                        quarterfinal_losers.append({
                            'place': 5,  # Tied for 5th
                            'participant': match.loser,
                            'is_team': False
                        })
            
            placings.extend(quarterfinal_losers)
    
    @staticmethod
    def _add_remaining_placings(placings, matches_by_round, is_doubles):
        """Add remaining places from earlier rounds"""
        for round_num in sorted(matches_by_round.keys()):
            # Skip already processed rounds
            if round_num <= 3 or round_num == 1.5:
                continue
            
            # Calculate place for this round's losers
            place = 2 ** (round_num - 1) + 1
            
            round_losers = []
            for match in matches_by_round[round_num]:
                if is_doubles:
                    if hasattr(match, 'losing_team_id') and match.losing_team_id:
                        round_losers.append({
                            'place': place,
                            'participant': match.loser,
                            'is_team': True
                        })
                else:
                    if hasattr(match, 'losing_player_id') and match.losing_player_id:
                        round_losers.append({
                            'place': place,
                            'participant': match.loser,
                            'is_team': False
                        })
            
            placings.extend(round_losers)
    
    @staticmethod
    def _calculate_points(category, place):
        """Calculate points for a specific placing"""
        # Check if category has custom points distribution
        
        if hasattr(category, 'points_distribution') and category.points_distribution:
            # Find matching place in distribution
            for place_range, percentage in category.points_distribution.items():
                if PlacingService._is_in_place_range(place, place_range):
                    return int(category.points_awarded * (percentage / 100))
        
        # Default points distribution if none specified
        # if place == 1:
        #     return category.points_awarded
        # elif place == 2:
        #     return int(category.points_awarded * 0.7)
        # elif place <= 4:
        #     return int(category.points_awarded * 0.5)
        # elif place <= 8:
        #     return int(category.points_awarded * 0.25)
        # elif place <= 16:
        #     return int(category.points_awarded * 0.15)
        
        return 0
    
    @staticmethod
    def _calculate_prize(category, place):
        """Calculate prize money for a specific placing"""
        # Get prize money for this category
        category_prize = 0
        if hasattr(category, 'prize_money'):
            category_prize = category.prize_money
        elif hasattr(category, 'prize_percentage') and category.tournament.prize_pool:
            # Calculate prize money based on percentage of total pool
            category_prize = category.tournament.prize_pool * (category.prize_percentage / 100)
        
        # If no prize money, return 0
        if category_prize <= 0:
            return 0

        
        # Check if category has custom prize distribution
        if hasattr(category, 'prize_distribution') and category.prize_distribution:
            # Find matching place in distribution
            for place_range, percentage in category.prize_distribution.items():
                if PlacingService._is_in_place_range(place, place_range):
                    return category_prize * (percentage / 100)
        

        # Default prize distribution if none specified
        # if place == 1:
        #     return category_prize * 0.5
        # elif place == 2:
        #     return category_prize * 0.25
        # elif place <= 4:
        #     return category_prize * 0.125
        # elif place <= 8:
        #     return category_prize * 0.0625
        
        return 0
    
    @staticmethod
    def _is_in_place_range(place, place_range):
        """Check if a place is within a range like '1', '2', '3-4', '5-8', etc."""
        if isinstance(place_range, int) or place_range.isdigit():
            return place == int(place_range)
        elif '-' in place_range:
            try:
                start, end = map(int, place_range.split('-'))
                return start <= place <= end
            except (ValueError, TypeError):
                pass
        
        return False