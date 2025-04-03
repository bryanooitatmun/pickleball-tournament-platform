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
            hasattr(m, 'stage') and (m.stage == MatchStage.KNOCKOUT or m.stage == MatchStage.PLAYOFF)
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
        
        # Get ALL matches in this group (both completed and incomplete)
        all_matches = []
        
        # Try using stage field if it exists
        if hasattr(Match, 'stage'):
            all_matches = Match.query.filter_by(
                group_id=group_id,
                stage=MatchStage.GROUP
            ).all()
        else:
            # Fallback: just get all matches with this group_id
            all_matches = Match.query.filter_by(
                group_id=group_id
            ).all()
        
        # Create a dict to track participant standings
        standings = {}
        
        # First, initialize standings for all participants in the group
        for match in all_matches:
            if category.is_doubles():
                # Add team1 to standings if not already there
                if match.team1_id and match.team1_id not in standings:
                    standing = GroupStanding.query.filter_by(
                        group_id=group_id, team_id=match.team1_id
                    ).first()
                    
                    if not standing:
                        standing = GroupStanding(
                            group_id=group_id,
                            team_id=match.team1_id
                        )
                        db.session.add(standing)
                    
                    # Reset all counters to zero
                    BracketService._reset_standing_counters(standing)
                    standings[match.team1_id] = standing
                
                # Add team2 to standings if not already there
                if match.team2_id and match.team2_id not in standings:
                    standing = GroupStanding.query.filter_by(
                        group_id=group_id, team_id=match.team2_id
                    ).first()
                    
                    if not standing:
                        standing = GroupStanding(
                            group_id=group_id,
                            team_id=match.team2_id
                        )
                        db.session.add(standing)
                    
                    # Reset all counters to zero
                    BracketService._reset_standing_counters(standing)
                    standings[match.team2_id] = standing
            else:
                # Add player1 to standings if not already there
                if match.player1_id and match.player1_id not in standings:
                    standing = GroupStanding.query.filter_by(
                        group_id=group_id, player_id=match.player1_id
                    ).first()
                    
                    if not standing:
                        standing = GroupStanding(
                            group_id=group_id,
                            player_id=match.player1_id
                        )
                        db.session.add(standing)
                    
                    # Reset all counters to zero
                    BracketService._reset_standing_counters(standing)
                    standings[match.player1_id] = standing
                
                # Add player2 to standings if not already there
                if match.player2_id and match.player2_id not in standings:
                    standing = GroupStanding.query.filter_by(
                        group_id=group_id, player_id=match.player2_id
                    ).first()
                    
                    if not standing:
                        standing = GroupStanding(
                            group_id=group_id,
                            player_id=match.player2_id
                        )
                        db.session.add(standing)
                    
                    # Reset all counters to zero
                    BracketService._reset_standing_counters(standing)
                    standings[match.player2_id] = standing
        
        # Process only completed matches to calculate standings from scratch
        completed_matches = [m for m in all_matches if m.completed]
        for match in completed_matches:
            BracketService._calculate_match_for_standings(match, standings, category.is_doubles())
        
        # Remove old standings that are no longer needed (if any)
        BracketService._clean_old_standings(standings, group_id)
        
        # Calculate final positions
        standings_list = list(standings.values())
        BracketService._calculate_group_positions(standings_list)
        
        db.session.commit()
        return standings_list

    @staticmethod
    def _reset_standing_counters(standing):
        """Reset all counters in a standing to zero"""
        standing.matches_played = 0
        standing.matches_won = 0
        standing.matches_lost = 0
        standing.sets_won = 0
        standing.sets_lost = 0
        standing.points_won = 0
        standing.points_lost = 0

    @staticmethod
    def _calculate_match_for_standings(match, standings, is_doubles):
        """
        Process a match to calculate standings
        This replaces _process_match_for_standings and avoids incrementing counters
        """
        if is_doubles:
            # Process team 1
            if match.team1_id and match.team1_id in standings:
                standing = standings[match.team1_id]
                # Increment matches played
                standing.matches_played += 1
                
                # Check who won
                if match.winning_team_id == match.team1_id:
                    standing.matches_won += 1
                else:
                    standing.matches_lost += 1
                
                # Process set scores
                scores = match.scores.all() if hasattr(match, 'scores') else MatchScore.query.filter_by(match_id=match.id).all()
                for score in scores:
                    if score.player1_score > score.player2_score:
                        standing.sets_won += 1
                    else:
                        standing.sets_lost += 1
                    
                    standing.points_won += score.player1_score
                    standing.points_lost += score.player2_score
            
            # Process team 2
            if match.team2_id and match.team2_id in standings:
                standing = standings[match.team2_id]
                # Increment matches played
                standing.matches_played += 1
                
                # Check who won
                if match.winning_team_id == match.team2_id:
                    standing.matches_won += 1
                else:
                    standing.matches_lost += 1
                
                # Process set scores
                scores = match.scores.all() if hasattr(match, 'scores') else MatchScore.query.filter_by(match_id=match.id).all()
                for score in scores:
                    if score.player2_score > score.player1_score:
                        standing.sets_won += 1
                    else:
                        standing.sets_lost += 1
                    
                    standing.points_won += score.player2_score
                    standing.points_lost += score.player1_score
        else:
            # Singles match
            # Process player 1
            if match.player1_id and match.player1_id in standings:
                standing = standings[match.player1_id]
                # Increment matches played
                standing.matches_played += 1
                
                # Check who won
                if match.winning_player_id == match.player1_id:
                    standing.matches_won += 1
                else:
                    standing.matches_lost += 1
                
                # Process set scores
                scores = match.scores.all() if hasattr(match, 'scores') else MatchScore.query.filter_by(match_id=match.id).all()
                for score in scores:
                    if score.player1_score > score.player2_score:
                        standing.sets_won += 1
                    else:
                        standing.sets_lost += 1
                    
                    standing.points_won += score.player1_score
                    standing.points_lost += score.player2_score
            
            # Process player 2
            if match.player2_id and match.player2_id in standings:
                standing = standings[match.player2_id]
                # Increment matches played
                standing.matches_played += 1
                
                # Check who won
                if match.winning_player_id == match.player2_id:
                    standing.matches_won += 1
                else:
                    standing.matches_lost += 1
                
                # Process set scores
                scores = match.scores.all() if hasattr(match, 'scores') else MatchScore.query.filter_by(match_id=match.id).all()
                for score in scores:
                    if score.player2_score > score.player1_score:
                        standing.sets_won += 1
                    else:
                        standing.sets_lost += 1
                    
                    standing.points_won += score.player2_score
                    standing.points_lost += score.player1_score

    @staticmethod
    def _clean_old_standings(standings, group_id):
        """Remove standings that are no longer needed"""
        participant_ids = list(standings.keys())
        
        # Don't delete anything if there are no participants
        if not participant_ids:
            return
        
        # Get IDs of teams and players in the standings
        team_ids = [pid for pid in participant_ids if standings[pid].team_id is not None]
        player_ids = [pid for pid in participant_ids if standings[pid].player_id is not None]
        
        # For teams - delete standings that aren't in our current list
        if team_ids:
            GroupStanding.query.filter(
                GroupStanding.group_id == group_id,
                GroupStanding.team_id.notin_(team_ids),
                GroupStanding.team_id.isnot(None)
            ).delete(synchronize_session=False)
        
        # For players - delete standings that aren't in our current list
        if player_ids:
            GroupStanding.query.filter(
                GroupStanding.group_id == group_id,
                GroupStanding.player_id.notin_(player_ids),
                GroupStanding.player_id.isnot(None)
            ).delete(synchronize_session=False)

    
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
    def _calculate_group_positions(standings):
        """
        Sort and assign positions to standings within a group.
        Uses the following tiebreak criteria in order:
        1. Matches won
        2. Head-to-head record with other tied players
        3. Point differential
        """
        if not standings:
            return
        
        # Step 1: Group standings by matches won (to identify ties)
        standings_by_wins = {}
        for standing in standings:
            wins = standing.matches_won
            if wins not in standings_by_wins:
                standings_by_wins[wins] = []
            standings_by_wins[wins].append(standing)
        
        # Step 2: Process each win group, applying tiebreakers where needed
        final_standings = []
        
        # Process win groups in descending order (most wins first)
        for wins in sorted(standings_by_wins.keys(), reverse=True):
            tied_standings = standings_by_wins[wins]
            
            # If only one participant with this win count, no tiebreaker needed
            if len(tied_standings) == 1:
                final_standings.append(tied_standings[0])
                continue
            
            # We have multiple participants with the same win count
            # Apply head-to-head tiebreaker
            sorted_tied = BracketService._apply_tiebreakers(tied_standings)
            final_standings.extend(sorted_tied)
        
        # Assign positions based on final order
        for i, standing in enumerate(final_standings, 1):
            standing.position = i

    @staticmethod
    def _apply_tiebreakers(tied_standings):
        """
        Apply tiebreakers to a group of standings with equal matches won.
        Primary: Head-to-head record
        Secondary: Point differential
        """
        if len(tied_standings) <= 1:
            return tied_standings
        
        # Get group ID (should be the same for all tied standings)
        group_id = tied_standings[0].group_id
        
        # Create a dictionary to track head-to-head records
        h2h_records = {}
        
        # Initialize head-to-head records
        for s in tied_standings:
            key = ('player', s.player_id) if s.player_id else ('team', s.team_id)
            h2h_records[key] = {
                'h2h_wins': 0,
                'original_standing': s
            }
        
        # Get all participant IDs for query
        player_ids = [s.player_id for s in tied_standings if s.player_id is not None]
        team_ids = [s.team_id for s in tied_standings if s.team_id is not None]
        
        # Query matches between tied participants
        all_h2h_matches = []
        
        # Get singles matches between tied players
        if player_ids:
            player_matches = Match.query.filter_by(
                group_id=group_id,
                completed=True
            ).filter(
                Match.player1_id.in_(player_ids),
                Match.player2_id.in_(player_ids)
            ).all()
            all_h2h_matches.extend(player_matches)
        
        # Get doubles matches between tied teams
        if team_ids:
            team_matches = Match.query.filter_by(
                group_id=group_id,
                completed=True
            ).filter(
                Match.team1_id.in_(team_ids),
                Match.team2_id.in_(team_ids)
            ).all()
            all_h2h_matches.extend(team_matches)
        
        # Process head-to-head matches
        for match in all_h2h_matches:
            # Singles match
            if match.player1_id and match.player2_id and match.player1_id in player_ids and match.player2_id in player_ids:
                p1_key = ('player', match.player1_id)
                p2_key = ('player', match.player2_id)
                
                # Only count if both players are in tied group (should always be true due to our filter)
                if p1_key in h2h_records and p2_key in h2h_records:
                    if match.winning_player_id == match.player1_id:
                        h2h_records[p1_key]['h2h_wins'] += 1
                    elif match.winning_player_id == match.player2_id:
                        h2h_records[p2_key]['h2h_wins'] += 1
            
            # Doubles match
            elif match.team1_id and match.team2_id and match.team1_id in team_ids and match.team2_id in team_ids:
                t1_key = ('team', match.team1_id)
                t2_key = ('team', match.team2_id)
                
                # Only count if both teams are in tied group (should always be true due to our filter)
                if t1_key in h2h_records and t2_key in h2h_records:
                    if match.winning_team_id == match.team1_id:
                        h2h_records[t1_key]['h2h_wins'] += 1
                    elif match.winning_team_id == match.team2_id:
                        h2h_records[t2_key]['h2h_wins'] += 1
        
        # Sort by head-to-head wins (primary), then point differential (secondary)
        sorted_tied = sorted(
            tied_standings,
            key=lambda s: (
                h2h_records[('player', s.player_id) if s.player_id else ('team', s.team_id)]['h2h_wins'],
                s.points_won - s.points_lost
            ),
            reverse=True
        )
        
        return sorted_tied

    @staticmethod
    def advance_winner(match):
        """
        Advances the winner to the next match and handles special cases like semifinal losers going to 3rd place playoffs
        
        Args:
            match: The completed match whose winner should advance
        """
        if not match.completed:
            # Match isn't complete yet, can't advance
            return False
        
        # --- First, handle the winner's advancement to the next match ---
        if match.next_match_id:
            # Get the next match
            next_match = Match.query.get(match.next_match_id)
            if next_match:
                # Determine whether winner goes to position 1 or 2 in the next match
                # Usually based on match_order: even goes to position 1, odd to position 2
                position = 1
                if hasattr(match, 'match_order') and match.match_order is not None:
                    position = 1 if match.match_order % 2 == 0 else 2
                
                # For doubles match
                if match.is_doubles:
                    if match.winning_team_id:
                        # Advance winner to the appropriate position
                        if position == 1:
                            next_match.team1_id = match.winning_team_id
                            if hasattr(match, 'player1_code') and match.player1_code:
                                next_match.player1_code = match.player1_code
                        else:
                            next_match.team2_id = match.winning_team_id
                            if hasattr(match, 'player2_code') and match.player2_code:
                                next_match.player2_code = match.player2_code
                
                # For singles match
                else:
                    if match.winning_player_id:
                        # Advance winner to the appropriate position
                        if position == 1:
                            next_match.player1_id = match.winning_player_id
                            if hasattr(match, 'player1_code') and match.player1_code:
                                next_match.player1_code = match.player1_code
                        else:
                            next_match.player2_id = match.winning_player_id
                            if hasattr(match, 'player2_code') and match.player2_code:
                                next_match.player2_code = match.player2_code
        
        # --- Second, check if this is a semifinal match (losers go to 3rd place match) ---
        # Semifinal round is typically round 2
        is_semifinal = (hasattr(match, 'round') and match.round == 2 and
                    hasattr(match, 'stage') and match.stage.name == 'KNOCKOUT')
        
        if is_semifinal and ((match.is_doubles and match.losing_team_id) or 
                            (not match.is_doubles and match.losing_player_id)):
            # Find the 3rd place match in the same category (typically round 1.5)
            third_place_match = Match.query.filter_by(
                category_id=match.category_id,
                round=1.5,
                stage=MatchStage.PLAYOFF
            ).first()
            
            if third_place_match:
                # Determine which position this semifinal loser should take in the 3rd place match
                # First semifinal loser goes to position 1, second to position 2
                position = 1
                if hasattr(match, 'match_order') and match.match_order is not None:
                    position = 1 if match.match_order % 2 == 0 else 2
                
                # For doubles match
                if match.is_doubles and match.losing_team_id:
                    # Advance loser to the appropriate position in 3rd place match
                    if position == 1:
                        third_place_match.team1_id = match.losing_team_id
                        if hasattr(match, 'player1_code') and match.player1_code:
                            third_place_match.player1_code = match.player1_code
                    else:
                        third_place_match.team2_id = match.losing_team_id
                        if hasattr(match, 'player2_code') and match.player2_code:
                            third_place_match.player2_code = match.player2_code
                
                # For singles match
                elif not match.is_doubles and match.losing_player_id:
                    # Advance loser to the appropriate position in 3rd place match
                    if position == 1:
                        third_place_match.player1_id = match.losing_player_id
                        if hasattr(match, 'player1_code') and match.player1_code:
                            third_place_match.player1_code = match.player1_code
                    else:
                        third_place_match.player2_id = match.losing_player_id
                        if hasattr(match, 'player2_code') and match.player2_code:
                            third_place_match.player2_code = match.player2_code
                    
        # Save changes
        db.session.commit()
        
        # Emit socket event to update brackets
        try:
            from app import socketio
            socketio.emit('bracket_update', {
                'tournament_id': match.category.tournament_id,
                'category_id': match.category_id
            }, room=f'tournament_{match.category.tournament_id}')
        except ImportError:
            # SocketIO might not be available
            pass
        
        return True