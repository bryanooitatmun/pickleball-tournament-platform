"""
Seed script for creating tournament brackets.
Generates groups and bracket matches for a tournament category.
"""

from app.models import (
    Tournament, TournamentCategory, Team, Match, MatchScore, Group, GroupStanding, Registration, MatchStage
)
from .seed_base import app, db, commit_changes
from datetime import datetime, timedelta
import random
import sys

def create_group(category, name, teams=None, commit=True):
    """Create a group for the tournament category"""
    # Check if group exists
    group = Group.query.filter_by(
        category_id=category.id,
        name=name
    ).first()
    
    if group:
        print(f"Group {name} for category {category.name} already exists")
        return group
    
    # Create group
    group = Group(
        category_id=category.id,
        name=name
    )
    db.session.add(group)
    db.session.flush()  # Get group ID without committing
    
    # Add teams to group if provided
    if teams:
        for team in teams:
            # Create standing
            standing = GroupStanding(
                group_id=group.id,
                team_id=team.id,
                matches_played=0,
                matches_won=0,
                matches_lost=0,
                sets_won=0,
                sets_lost=0,
                points_won=0,
                points_lost=0,
                position=None  # Will be calculated after matches
            )
            db.session.add(standing)
    
    if commit:
        commit_changes(f"Group {name} created with {len(teams) if teams else 0} teams")
    
    return group

def create_group_matches(group, teams, percentage_completed=100, commit=True):
    """Create round-robin matches for a group"""
    # Check if matches already exist for this group
    existing_matches = Match.query.filter_by(group_id=group.id).count()
    if existing_matches > 0:
        print(f"Matches for group {group.name} already exist")
        return []
    
    matches = []
    match_number = 1
    
    # Create round-robin matches
    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            team1 = teams[i]
            team2 = teams[j]
            
            # Determine if the match is completed
            completed = random.random() < (percentage_completed / 100)
            
            # Create match
            match = Match(
                category_id=group.category_id,
                group_id=group.id,
                round=match_number,
                stage=MatchStage.GROUP,
                match_order=match_number,
                team1_id=team1.id,
                team2_id=team2.id,
                completed=completed,
                court=f"Court {random.randint(1, 8)}",
                scheduled_time=datetime.now() + timedelta(hours=random.randint(-12, 24)),
                referee_verified=completed,
                player_verified=completed if random.random() < 0.7 else False,
                livestream_url=f"https://youtube.com/watch?v=pickleball{random.randint(1, 1000)}" if random.random() < 0.3 else None
            )
            
            if completed:
                # Bias towards higher seeds
                seed_diff = teams.index(team1) - teams.index(team2)
                higher_seed_advantage = 0.5 + min(0.4, abs(seed_diff) * 0.05) * (1 if seed_diff < 0 else -1)
                
                team1_wins = random.random() < higher_seed_advantage
                
                if team1_wins:
                    match.winning_team_id = team1.id
                    match.losing_team_id = team2.id
                else:
                    match.winning_team_id = team2.id
                    match.losing_team_id = team1.id
                
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
            matches.append(match)
            match_number += 1
    
    if commit:
        commit_changes(f"Created {len(matches)} matches for group {group.name}")
    
    return matches

def calculate_group_standings(group, commit=True):
    """Calculate standings positions based on match results"""
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
    
    if commit:
        commit_changes(f"Calculated standings for group {group.name}")
    
    return standings


def create_knockout_matches(category, group_qualifiers, percentage_completed=75, commit=True):
    """Create knockout stage matches for the tournament"""
    # Check if knockout matches already exist
    existing_matches = Match.query.filter(
        Match.category_id == category.id,
        Match.group_id.is_(None),  # Knockout matches don't have group_id
        Match.round <= 4  # Rounds 1-4 are knockout (final, semis, quarters)
    ).count()
    
    if existing_matches > 0:
        print(f"Knockout matches for {category.name} already exist")
        return []
    
    # Extract teams from group qualifiers: {group_name: [group_obj, [1st_place_team, 2nd_place_team]]}
    # We expect keys 'A', 'B', 'C', 'D'
    
    # Create quarterfinal matches with the specific format requested:
    # Top of bracket: A1 vs D2, B1 vs C2
    # Bottom of bracket: C1 vs B2, D1 vs A2
    qf_matchups = [
        (group_qualifiers['A'][1][0], group_qualifiers['D'][1][1]),  # A1 vs D2
        (group_qualifiers['B'][1][0], group_qualifiers['C'][1][1]),  # B1 vs C2
        (group_qualifiers['C'][1][0], group_qualifiers['B'][1][1]),  # C1 vs B2
        (group_qualifiers['D'][1][0], group_qualifiers['A'][1][1]),  # D1 vs A2
    ]
    
    # Create a flat list of all qualified teams for seed advantage calculation
    all_qualified_teams = []
    for group_letter in ['A', 'B', 'C', 'D']:
        if group_letter in group_qualifiers:
            all_qualified_teams.extend(group_qualifiers[group_letter][1])
    
    qf_matches = []
    for idx, (team1, team2) in enumerate(qf_matchups):
        # Determine if match is completed
        completed = random.random() < (percentage_completed / 100)
        
        match = Match(
            category_id=category.id,
            round=3,  # Quarterfinals
            stage=MatchStage.KNOCKOUT,
            match_order=idx + 1,
            team1_id=team1.id,
            team2_id=team2.id,
            completed=completed,
            court=f"Court {random.randint(1, 4)}",
            scheduled_time=datetime.now() + timedelta(hours=random.randint(24, 36)),
            referee_verified=completed,
            player_verified=completed if random.random() < 0.7 else False,
            livestream_url=f"https://youtube.com/watch?v=pickleball{random.randint(1000, 2000)}" if random.random() < 0.5 else None
        )
        
        if completed:
            # Higher seed advantage based on a list of all qualified teams
            # First position in a group is ranked higher than second position in a group
            team1_idx = all_qualified_teams.index(team1)
            team2_idx = all_qualified_teams.index(team2)
            seed_diff = team1_idx - team2_idx
            higher_seed_advantage = 0.5 + min(0.3, abs(seed_diff) * 0.05) * (1 if seed_diff < 0 else -1)
            
            team1_wins = random.random() < higher_seed_advantage
            
            if team1_wins:
                match.winning_team_id = team1.id
                match.losing_team_id = team2.id
            else:
                match.winning_team_id = team2.id
                match.losing_team_id = team1.id
            
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
    
    if commit:
        commit_changes(f"Created {len(qf_matches)} quarterfinal matches for {category.name}")
    
    # Create semifinal matches
    sf_matches = []
    
    # First semifinal: QF1 winner vs QF2 winner
    sf1 = Match(
        category_id=category.id,
        round=2,  # Semifinals
        stage=MatchStage.KNOCKOUT,
        match_order=1,
        team1_id=qf_matches[0].winning_team_id if qf_matches[0].completed else None,
        team2_id=qf_matches[1].winning_team_id if qf_matches[1].completed else None,
        completed=False,  # Pending
        court="Court 1",
        scheduled_time=datetime.now() + timedelta(hours=48),
        referee_verified=False,
        player_verified=False,
        player1_code="SF1",  # Add position code
        player2_code="SF2"   # Add position code
    )
    db.session.add(sf1)
    sf_matches.append(sf1)
    db.session.flush()
    # Second semifinal: QF3 winner vs QF4 winner
    sf2 = Match(
        category_id=category.id,
        round=2,  # Semifinals
        stage=MatchStage.KNOCKOUT,
        match_order=2,
        team1_id=qf_matches[2].winning_team_id if qf_matches[2].completed else None,
        team2_id=qf_matches[3].winning_team_id if qf_matches[3].completed else None,
        completed=False,  # Pending
        court="Court 2",
        scheduled_time=datetime.now() + timedelta(hours=48),
        referee_verified=False,
        player_verified=False,
        player1_code="SF3",  # Add position code
        player2_code="SF4"   # Add position code
    )
    db.session.add(sf2)
    sf_matches.append(sf2)
    db.session.flush()

    # Set next_match_id for quarterfinals
    qf_matches[0].next_match_id = sf1.id  # QF1 winner goes to SF1
    qf_matches[1].next_match_id = sf1.id  # QF2 winner goes to SF1
    qf_matches[2].next_match_id = sf2.id  # QF3 winner goes to SF2
    qf_matches[3].next_match_id = sf2.id  # QF4 winner goes to SF2
    
    if commit:
        commit_changes(f"Created {len(sf_matches)} semifinal matches for {category.name}")
    
    # Create the final match
    final_match = Match(
        category_id=category.id,
        round=1,  # Finals
        stage=MatchStage.KNOCKOUT,
        match_order=1,
        # Don't set team IDs yet - they'll be determined by semifinal winners
        completed=False,
        court="Center Court",
        scheduled_time=datetime.now() + timedelta(hours=72),  # 3 days from now
        referee_verified=False,
        player_verified=False,
        player1_code="W-SF1",  # Winner of first semifinal
        player2_code="W-SF2",  # Winner of second semifinal
        livestream_url=f"https://youtube.com/watch?v=pickleball_finals_{random.randint(5000, 6000)}"
    )
    db.session.add(final_match)
    db.session.flush()

    # Set next_match_id for semifinals
    sf1.next_match_id = final_match.id  # SF1 winner goes to Final
    sf2.next_match_id = final_match.id  # SF2 winner goes to Final
    
    if commit:
        commit_changes(f"Created final match for {category.name}")
    
    result_matches = qf_matches + sf_matches + [final_match]
    return result_matches

def seed_mens_doubles_bracket(category_name="Men's Doubles Open", commit=True):
    """Seed Men's Doubles bracket with groups and knockout stage"""
    # Get tournament
    tournament = Tournament.query.filter_by(name="SportsSync-Oncourt Pickleball Tournament").first()
    if not tournament:
        print("Tournament not found. Please run seed_tournament.py first.")
        return
    
    # Get category
    category = TournamentCategory.query.filter_by(
        tournament_id=tournament.id,
        name=category_name
    ).first()
    
    if not category:
        print(f"Category '{category_name}' not found.")
        return
    
    # Get teams for this category
    teams = Team.query.filter_by(category_id=category.id).all()
    
    if not teams:
        print(f"No teams found for {category_name}.")
        return
    
    # Create 4 groups with 4 teams each
    if len(teams) >= 16:
        # Sort teams by seed (None values at the end)
        team_registrations = []
        for team in teams:
            reg = Registration.query.filter_by(
                category_id=category.id,
                player_id=team.player1_id,
                partner_id=team.player2_id
            ).first()
            if reg:
                team_registrations.append((team, reg.seed or 999))
        
        # Sort by seed (lower seed first, None values at the end)
        team_registrations.sort(key=lambda x: x[1] if x[1] is not None else 999)
        sorted_teams = [tr[0] for tr in team_registrations]
        
        # Initialize groups
        groups = []
        
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
        
        for i, indices in enumerate(group_distribution):
            # Get teams for this group
            group_teams = [sorted_teams[idx] for idx in indices if idx < len(sorted_teams)]
            
            # Create group
            group = create_group(category, f"Group {chr(65+i)}", group_teams, commit=False)  # A, B, C, D
            groups.append(group)
            
            # Create group matches
            create_group_matches(group, group_teams, percentage_completed=100, commit=False)
            
            # Calculate standings
            calculate_group_standings(group, commit=False)
        
        # Create knockout phase with top 2 teams from each group
        # Organize by group for the specific knockout pairing structure
        group_qualifiers = {}
        for i, group in enumerate(groups):
            group_letter = chr(65+i)  # A, B, C, D
            top_teams = GroupStanding.query.filter(
                GroupStanding.group_id == group.id,
                GroupStanding.position <= 2
            ).order_by(GroupStanding.position).all()
            
            qualified_group_teams = []
            for standing in top_teams:
                team = Team.query.get(standing.team_id)
                qualified_group_teams.append(team)
            
            group_qualifiers[group_letter] = (group, qualified_group_teams)
        
        # Create knockout matches with the specific pairing structure
        create_knockout_matches(category, group_qualifiers, percentage_completed=100, commit=False)
        
        if commit:
            commit_changes(f"Created complete bracket for {category_name}")
        
        print(f"Created 4 groups and knockout stage for {category_name}")
        return groups
    else:
        print(f"Not enough teams for {category_name}. Need at least 16 teams.")
        return []

def main():
    """Run when this script is executed directly"""
    # Seed men's doubles bracket
    groups = seed_mens_doubles_bracket()
    if groups:
        print(f"Created {len(groups)} groups for Men's Doubles Open")
        for group in groups:
            standings = GroupStanding.query.filter_by(group_id=group.id).count()
            print(f"  - {group.name}: {standings} teams")

if __name__ == "__main__":
    with app.app_context():
        main()
