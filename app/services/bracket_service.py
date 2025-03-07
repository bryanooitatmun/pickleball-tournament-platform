from app import db
from app.models import Tournament, TournamentCategory, Match, MatchScore, Group, GroupStanding, TournamentFormat
from app.models import MatchStage
from sqlalchemy import func
from collections import defaultdict

class BracketService:
    """Service for generating and managing tournament brackets"""
    
    @staticmethod
    def get_bracket_data(category_id):
        """
        Get comprehensive bracket data for a category
        Returns matches by stage (group/knockout), standings for groups,
        and other metadata needed for bracket visualization
        """
        category = TournamentCategory.query.get_or_404(category_id)
        tournament = category.tournament
        
        result = {
            'category': category,
            'format': tournament.format,
            'group_stage': False,
            'groups': [],
            'knockout_rounds': {},
            'placings': []
        }
        
        # Check if this tournament has group stages
        if tournament.format == TournamentFormat.GROUP_KNOCKOUT:
            result['group_stage'] = True
            result['groups'] = BracketService.get_group_data(category_id)
        
        # Get all matches for the category
        all_matches = Match.query.filter_by(category_id=category_id).all()
        
        # Organize knockout matches by round
        knockout_matches = [m for m in all_matches if (
            hasattr(m, 'stage') and m.stage == MatchStage.KNOCKOUT
        ) or (
            not hasattr(m, 'stage') and (not hasattr(m, 'group_id') or m.group_id is None)
        )]
        
        for match in knockout_matches:
            round_num = match.round
            if round_num not in result['knockout_rounds']:
                result['knockout_rounds'][round_num] = []
            result['knockout_rounds'][round_num].append(match)
        
        # Sort matches within each round by match_order
        for round_num in result['knockout_rounds']:
            result['knockout_rounds'][round_num].sort(key=lambda m: m.match_order)
        
        # Get tournament placings if completed
        if tournament.status == 'COMPLETED':
            try:
                # Try to import PlacingService if it exists
                from app.services.placing_service import PlacingService
                result['placings'] = PlacingService.get_placings(category_id)
            except ImportError:
                # If PlacingService doesn't exist yet, just return empty placings
                result['placings'] = []
        
        return result
    
    @staticmethod
    def get_group_data(category_id):
        """Get all group data including standings and matches"""
        # Get all groups for this category
        groups = Group.query.filter_by(category_id=category_id).all()
        
        group_data = []
        for group in groups:
            # Get standings for this group
            standings = GroupStanding.query.filter_by(group_id=group.id)\
                .order_by(GroupStanding.position).all()
            
            # Get matches for this group
            group_matches = []
            
            # Try using the stage field if it exists in the Match model
            if hasattr(Match, 'stage'):
                group_matches = Match.query.filter_by(
                    group_id=group.id,
                    stage=MatchStage.GROUP
                ).order_by(Match.match_order).all()
            else:
                # Fallback: just get matches with this group_id
                group_matches = Match.query.filter_by(
                    group_id=group.id
                ).order_by(Match.match_order).all()
            
            group_data.append({
                'group': group,
                'standings': standings,
                'matches': group_matches
            })
        
        return group_data
    
    @staticmethod
    def update_group_standings(group_id):
        """Update standings for a group based on match results"""
        group = Group.query.get_or_404(group_id)
        category = group.category
        
        # Get all completed matches in this group
        completed_matches = []
        
        # Try using stage field if it exists
        if hasattr(Match, 'stage'):
            completed_matches = Match.query.filter_by(
                group_id=group_id, 
                completed=True,
                stage=MatchStage.GROUP
            ).all()
        else:
            # Fallback: just get completed matches with this group_id
            completed_matches = Match.query.filter_by(
                group_id=group_id, 
                completed=True
            ).all()
        
        # Create a dict to track participant standings
        standings = {}
        
        # Process each match to update standings
        for match in completed_matches:
            BracketService._process_match_for_standings(match, standings, category.is_doubles())
        
        # Update database standings
        BracketService._update_database_standings(standings, group_id)
        
        # Calculate final positions
        standings_list = list(standings.values())
        BracketService._calculate_group_positions(standings_list)
        
        db.session.commit()
        return standings_list
    
    @staticmethod
    def _process_match_for_standings(match, standings, is_doubles):
        """Process a match to update the standings dictionary"""
        if is_doubles:
            # Process team 1
            if match.team1_id:
                if match.team1_id not in standings:
                    standing = GroupStanding.query.filter_by(
                        group_id=match.group_id, team_id=match.team1_id
                    ).first()
                    
                    if not standing:
                        standing = GroupStanding(
                            group_id=match.group_id,
                            team_id=match.team1_id
                        )
                        db.session.add(standing)
                    
                    standings[match.team1_id] = standing
                
                # Update standing with match results
                BracketService._update_standing_from_match(standings[match.team1_id], match, is_team1=True)
            
            # Process team 2
            if match.team2_id:
                if match.team2_id not in standings:
                    standing = GroupStanding.query.filter_by(
                        group_id=match.group_id, team_id=match.team2_id
                    ).first()
                    
                    if not standing:
                        standing = GroupStanding(
                            group_id=match.group_id,
                            team_id=match.team2_id
                        )
                        db.session.add(standing)
                    
                    standings[match.team2_id] = standing
                
                # Update standing with match results
                BracketService._update_standing_from_match(standings[match.team2_id], match, is_team1=False)
        else:
            # Process player 1
            if match.player1_id:
                if match.player1_id not in standings:
                    standing = GroupStanding.query.filter_by(
                        group_id=match.group_id, player_id=match.player1_id
                    ).first()
                    
                    if not standing:
                        standing = GroupStanding(
                            group_id=match.group_id,
                            player_id=match.player1_id
                        )
                        db.session.add(standing)
                    
                    standings[match.player1_id] = standing
                
                # Update standing with match results
                BracketService._update_standing_from_match(standings[match.player1_id], match, is_team1=True)
            
            # Process player 2
            if match.player2_id:
                if match.player2_id not in standings:
                    standing = GroupStanding.query.filter_by(
                        group_id=match.group_id, player_id=match.player2_id
                    ).first()
                    
                    if not standing:
                        standing = GroupStanding(
                            group_id=match.group_id,
                            player_id=match.player2_id
                        )
                        db.session.add(standing)
                    
                    standings[match.player2_id] = standing
                
                # Update standing with match results
                BracketService._update_standing_from_match(standings[match.player2_id], match, is_team1=False)
    
    @staticmethod
    def _update_database_standings(standings, group_id):
        """Update database with standings"""
        # First delete any existing standings not in our current list
        participant_ids = list(standings.keys())
        
        # Remove old standings that are no longer needed
        if len(participant_ids) > 0:
            # For teams
            team_ids = [pid for pid in participant_ids if standings[pid].team_id is not None]
            if team_ids:
                GroupStanding.query.filter(
                    GroupStanding.group_id == group_id,
                    GroupStanding.team_id.notin_(team_ids),
                    GroupStanding.team_id.isnot(None)
                ).delete(synchronize_session=False)
            
            # For players
            player_ids = [pid for pid in participant_ids if standings[pid].player_id is not None]
            if player_ids:
                GroupStanding.query.filter(
                    GroupStanding.group_id == group_id,
                    GroupStanding.player_id.notin_(player_ids),
                    GroupStanding.player_id.isnot(None)
                ).delete(synchronize_session=False)
    
    @staticmethod
    def _update_standing_from_match(standing, match, is_team1):
        """Update standing based on a match result"""
        # Increment matches played counter
        standing.matches_played = standing.matches_played + 1
        
        # Check who won the match
        if is_team1:
            if hasattr(match, 'is_doubles') and match.is_doubles:
                if match.winning_team_id == match.team1_id:
                    standing.matches_won = standing.matches_won + 1
                else:
                    standing.matches_lost = standing.matches_lost + 1
            else:
                if match.winning_player_id == match.player1_id:
                    standing.matches_won = standing.matches_won + 1
                else:
                    standing.matches_lost = standing.matches_lost + 1
        else:
            if hasattr(match, 'is_doubles') and match.is_doubles:
                if match.winning_team_id == match.team2_id:
                    standing.matches_won = standing.matches_won + 1
                else:
                    standing.matches_lost = standing.matches_lost + 1
            else:
                if match.winning_player_id == match.player2_id:
                    standing.matches_won = standing.matches_won + 1
                else:
                    standing.matches_lost = standing.matches_lost + 1
        
        # Process set scores
        scores = match.scores if hasattr(match, 'scores') else MatchScore.query.filter_by(match_id=match.id).all()
        
        for score in scores:
            if is_team1:
                if score.player1_score > score.player2_score:
                    standing.sets_won = standing.sets_won + 1
                else:
                    standing.sets_lost = standing.sets_lost + 1
                
                # Add points
                standing.points_won = standing.points_won + score.player1_score
                standing.points_lost = standing.points_lost + score.player2_score
            else:
                if score.player2_score > score.player1_score:
                    standing.sets_won = standing.sets_won + 1
                else:
                    standing.sets_lost = standing.sets_lost + 1
                
                # Add points
                standing.points_won = standing.points_won + score.player2_score
                standing.points_lost = standing.points_lost + score.player1_score
    
    @staticmethod
    def _calculate_group_positions(standings):
        """Sort and assign positions to standings within a group"""
        # Sort by matches won, then by set differential, then by point differential
        sorted_standings = sorted(
            standings,
            key=lambda s: (
                s.matches_won,
                s.sets_won - s.sets_lost,
                s.points_won - s.points_lost
            ),
            reverse=True
        )
        
        # Assign positions
        for i, standing in enumerate(sorted_standings, 1):
            standing.position = i