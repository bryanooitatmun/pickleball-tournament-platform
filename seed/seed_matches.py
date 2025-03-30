"""
Seed script for match scheduling, scoring, and verification.
Handles match court assignments, scheduled times, and verification status.
"""

from app.models import Tournament, TournamentCategory, Match, MatchScore, User, UserRole
from seed_base import app, db, commit_changes
from datetime import datetime, timedelta
import random
import sys

def assign_match_courts_and_times(tournament, commit=True):
    """Assign courts and scheduled times to all matches in a tournament"""
    # Get all matches for the tournament
    matches = Match.query.join(TournamentCategory).filter(
        TournamentCategory.tournament_id == tournament.id,
        Match.court.is_(None) | Match.scheduled_time.is_(None)
    ).all()
    
    if not matches:
        print("No matches needing court/time assignment")
        return 0
    
    # Get tournament dates for scheduling
    tournament_days = []
    current_date = tournament.start_date.date()
    while current_date <= tournament.end_date.date():
        tournament_days.append(current_date)
        current_date += timedelta(days=1)
    
    # Get venue court count
    court_count = tournament.venue.court_count if tournament.venue and tournament.venue.court_count else 8
    
    # Available courts
    courts = [f"Court {i}" for i in range(1, court_count + 1)]
    
    # Schedule matches
    updated_count = 0
    
    # Group matches by round (higher rounds first - finals, semis, etc.)
    round_matches = {}
    for match in matches:
        if match.round not in round_matches:
            round_matches[match.round] = []
        round_matches[match.round].append(match)
    
    # Order rounds (lower number = later stages, e.g. 1 = final)
    ordered_rounds = sorted(round_matches.keys())
    
    # Schedule group matches first, then knockout rounds
    group_matches = [m for m in matches if m.group_id is not None]
    knockout_matches = [m for m in matches if m.group_id is None]
    
    # Day 1: Group Matches
    # Schedule group matches on the first day(s)
    if group_matches:
        day_index = 0
        match_day = tournament_days[day_index]
        match_time = datetime.combine(match_day, datetime.min.time()) + timedelta(hours=9)  # Start at 9 AM
        
        for match in group_matches:
            # Assign court
            match.court = courts[updated_count % len(courts)]
            
            # Assign time (30 min per match)
            match.scheduled_time = match_time
            match_time += timedelta(minutes=30)
            
            # If we've scheduled 16 matches (8 hours of play), move to next day
            if updated_count > 0 and updated_count % 16 == 0:
                day_index = min(day_index + 1, len(tournament_days) - 1)
                match_day = tournament_days[day_index]
                match_time = datetime.combine(match_day, datetime.min.time()) + timedelta(hours=9)
            
            updated_count += 1
    
    # Schedule knockout matches on later day(s)
    if knockout_matches:
        # Use last day for finals
        finals_day = tournament_days[-1]
        
        # Start with early rounds (higher round numbers)
        for round_num in reversed(ordered_rounds):
            if round_num in [1, 2]:  # Finals and Semifinals on the last day
                match_day = finals_day
            else:  # Earlier rounds on second-to-last day
                match_day = tournament_days[-2] if len(tournament_days) > 1 else finals_day
            
            # Time depends on round (finals later in the day)
            if round_num == 1:  # Final
                match_time = datetime.combine(match_day, datetime.min.time()) + timedelta(hours=16)  # 4 PM
            elif round_num == 2:  # Semifinals
                match_time = datetime.combine(match_day, datetime.min.time()) + timedelta(hours=14)  # 2 PM
            else:  # Earlier rounds
                match_time = datetime.combine(match_day, datetime.min.time()) + timedelta(hours=10)  # 10 AM
            
            # Schedule matches for this round
            for match in round_matches.get(round_num, []):
                if match.group_id is None:  # Only knockout matches
                    # Assign court (better courts for later rounds)
                    if round_num <= 2:  # Finals and Semifinals on courts 1-2
                        match.court = courts[match.match_order - 1 % 2]
                    else:
                        match.court = courts[match.match_order % len(courts)]
                    
                    # Assign time (45 min per match for later rounds)
                    match.scheduled_time = match_time
                    match_time += timedelta(minutes=45 if round_num <= 2 else 30)
                    
                    updated_count += 1
    
    # Add livestream to some high-profile matches
    for match in matches:
        if match.round <= 2 or random.random() < 0.2:  # Finals, semifinals, and 20% of other matches
            match.livestream_url = f"https://youtube.com/watch?v=pickleball{random.randint(1000, 9999)}"
    
    if commit:
        commit_changes(f"Assigned courts and times to {updated_count} matches")
    
    return updated_count

def add_match_verification(tournament, commit=True):
    """Add referee and player verification to completed matches"""
    # Get completed matches without verification
    matches = Match.query.join(TournamentCategory).filter(
        TournamentCategory.tournament_id == tournament.id,
        Match.completed == True,
        (Match.referee_verified == False) | (Match.player_verified == False)
    ).all()
    
    if not matches:
        print("No completed matches needing verification")
        return 0
    
    # Get a referee
    referee = User.query.filter_by(role=UserRole.REFEREE).first()
    if not referee:
        print("No referee found - verification status may be incomplete")
    
    updated_count = 0
    for match in matches:
        # 80% chance of referee verification
        if random.random() < 0.8:
            match.referee_verified = True
            
            # 70% chance of player verification if referee verified
            if match.referee_verified and random.random() < 0.7:
                match.player_verified = True
            
            updated_count += 1
    
    if commit:
        commit_changes(f"Added verification to {updated_count} matches")
    
    return updated_count

def update_match_scores(tournament, commit=True):
    """Update scores for completed matches"""
    # Get completed matches without scores
    matches = Match.query.join(TournamentCategory).filter(
        TournamentCategory.tournament_id == tournament.id,
        Match.completed == True
    ).all()
    
    if not matches:
        print("No completed matches to update scores")
        return 0
    
    updated_count = 0
    for match in matches:
        # Check if match already has scores
        existing_scores = MatchScore.query.filter_by(match_id=match.id).count()
        if existing_scores > 0:
            continue
        
        # Create score
        score = MatchScore(
            match_id=match.id,
            set_number=1
        )
        
        # Set appropriate scores based on winner
        if match.is_team_match:
            if match.team1_id == match.winning_team_id:
                score.player1_score = 11
                score.player2_score = random.randint(5, 9)
            else:
                score.player1_score = random.randint(5, 9)
                score.player2_score = 11
        else:
            if match.player1_id == match.winning_player_id:
                score.player1_score = 11
                score.player2_score = random.randint(5, 9)
            else:
                score.player1_score = random.randint(5, 9)
                score.player2_score = 11
        
        db.session.add(score)
        updated_count += 1
    
    if commit:
        commit_changes(f"Updated scores for {updated_count} matches")
    
    return updated_count

def main():
    """Run when this script is executed directly"""
    # Get tournament
    tournament = Tournament.query.filter_by(name="SportsSync-Oncourt Pickleball Tournament").first()
    if not tournament:
        print("Tournament not found. Please run seed_tournament.py first.")
        return
    
    # Assign courts and times
    updated_courts = assign_match_courts_and_times(tournament)
    print(f"Assigned courts and times to {updated_courts} matches")
    
    # Update match scores
    updated_scores = update_match_scores(tournament)
    print(f"Updated scores for {updated_scores} matches")
    
    # Add verification status
    updated_verification = add_match_verification(tournament)
    print(f"Added verification to {updated_verification} matches")

if __name__ == "__main__":
    with app.app_context():
        main()
