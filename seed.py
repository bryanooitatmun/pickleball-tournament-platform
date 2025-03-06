"""
Updated seed script that works with the new Team model for doubles matches
"""

import os
import sys
from datetime import datetime, timedelta
import random
from flask import Flask
from config import Config
from app import create_app, db
from app.models import (User, UserRole, PlayerProfile, Tournament, TournamentCategory, 
                       Registration, TournamentTier, TournamentFormat, CategoryType, 
                       TournamentStatus, Match, MatchScore, Equipment, Sponsor, Team)

def seed_users():
    print("Seeding users...")
    # First check if users already exist
    if User.query.count() > 0:
        print("Users already exist, skipping...")
        admin = User.query.filter_by(role=UserRole.ADMIN).first()
        organizer = User.query.filter_by(role=UserRole.ORGANIZER).first()
        players = User.query.filter_by(role=UserRole.PLAYER).all()
        return admin, organizer, players
    
    admin = User(
        username="admin",
        email="admin@example.com",
        role=UserRole.ADMIN,
        created_at=datetime.utcnow()
    )
    admin.set_password("password")
    db.session.add(admin)
    
    organizer = User(
        username="organizer",
        email="organizer@example.com",
        role=UserRole.ORGANIZER,
        created_at=datetime.utcnow()
    )
    organizer.set_password("password")
    db.session.add(organizer)
    
    # Create 20 player users
    player_users = []
    for i in range(1, 21):
        player = User(
            username=f"player{i}",
            email=f"player{i}@example.com",
            role=UserRole.PLAYER,
            created_at=datetime.utcnow() - timedelta(days=random.randint(0, 30))
        )
        player.set_password("password")
        db.session.add(player)
        player_users.append(player)
    
    db.session.commit()
    
    return admin, organizer, player_users

def seed_player_profiles(player_users):
    print("Seeding player profiles...")
    # Check if profiles already exist
    if PlayerProfile.query.count() > 0:
        print("Player profiles already exist, skipping...")
        return PlayerProfile.query.all()
    
    player_profiles = []
    
    countries = ["USA", "Canada", "Mexico", "Brazil", "Spain", "France", "Italy", "UK", "Germany", "Japan"]
    cities = ["New York", "Los Angeles", "Toronto", "Mexico City", "Rio", "Barcelona", "Paris", "Rome", "London", "Berlin", "Tokyo"]
    
    for i, user in enumerate(player_users):
        # Random stats
        country = random.choice(countries)
        city = random.choice(cities)
        age = random.randint(18, 45)
        plays = "Right-handed" if random.random() > 0.2 else "Left-handed"
        turned_pro = random.randint(2010, 2022)
        
        # Random ranking points
        mens_singles = random.randint(0, 5000) if i % 2 == 0 else 0
        womens_singles = random.randint(0, 5000) if i % 2 == 1 else 0
        mens_doubles = random.randint(0, 4000) if i % 3 == 0 else 0
        womens_doubles = random.randint(0, 4000) if i % 3 == 1 else 0
        mixed_doubles = random.randint(0, 3500) if i % 3 == 2 else 0
        
        profile = PlayerProfile(
            user_id=user.id,
            full_name=f"{['John', 'Jane', 'Alex', 'Maria', 'Carlos', 'Emma', 'David', 'Sofia'][i % 8]} {['Smith', 'Johnson', 'Williams', 'Jones', 'Brown', 'Garcia', 'Martinez', 'Lopez'][i % 8]}",
            country=country,
            city=city,
            age=age,
            bio=f"Professional pickleball player from {city}, {country}. Started playing in {turned_pro}.",
            plays=plays,
            height=f"{random.randint(5, 6)}'{random.randint(0, 11)}\"",
            paddle="ProKennex Ovation Flight",
            turned_pro=turned_pro,
            mens_singles_points=mens_singles,
            womens_singles_points=womens_singles,
            mens_doubles_points=mens_doubles,
            womens_doubles_points=womens_doubles,
            mixed_doubles_points=mixed_doubles
        )
        
        db.session.add(profile)
        player_profiles.append(profile)
    
    db.session.commit()
    
    return player_profiles

def seed_tournaments(organizer):
    print("Seeding tournaments...")
    # Check if tournaments already exist
    if Tournament.query.count() > 0:
        print("Tournaments already exist, skipping...")
        return Tournament.query.all()
    
    tournaments = []
    
    # Past tournament (completed)
    past_tournament = Tournament(
        name="Rocky Mountain Championship",
        organizer_id=organizer.id,
        location="Denver, Colorado",
        description="The premier pickleball event in the Rocky Mountains featuring top talent from across the country.",
        start_date=datetime.utcnow() - timedelta(days=60),
        end_date=datetime.utcnow() - timedelta(days=57),
        registration_deadline=datetime.utcnow() - timedelta(days=75),
        tier=TournamentTier.OPEN,
        format=TournamentFormat.SINGLE_ELIMINATION,
        status=TournamentStatus.COMPLETED,
        prize_pool=25000.0,
        registration_fee=150.0
    )
    db.session.add(past_tournament)
    tournaments.append(past_tournament)
    
    # Current tournament (ongoing)
    current_tournament = Tournament(
        name="Coastal Classic",
        organizer_id=organizer.id,
        location="Miami, Florida",
        description="Experience pickleball at its finest with ocean views and top competition.",
        start_date=datetime.utcnow() - timedelta(days=1),
        end_date=datetime.utcnow() + timedelta(days=2),
        registration_deadline=datetime.utcnow() - timedelta(days=14),
        tier=TournamentTier.CHALLENGE,
        format=TournamentFormat.DOUBLE_ELIMINATION,
        status=TournamentStatus.ONGOING,
        prize_pool=15000.0,
        registration_fee=120.0
    )
    db.session.add(current_tournament)
    tournaments.append(current_tournament)
    
    # Future tournament (upcoming)
    future_tournament = Tournament(
        name="Midwest Masters",
        organizer_id=organizer.id,
        location="Chicago, Illinois",
        description="The biggest pickleball tournament in the Midwest featuring all categories and skill levels.",
        start_date=datetime.utcnow() + timedelta(days=30),
        end_date=datetime.utcnow() + timedelta(days=33),
        registration_deadline=datetime.utcnow() + timedelta(days=15),
        tier=TournamentTier.CUP,
        format=TournamentFormat.SINGLE_ELIMINATION,
        status=TournamentStatus.UPCOMING,
        prize_pool=35000.0,
        registration_fee=200.0
    )
    db.session.add(future_tournament)
    tournaments.append(future_tournament)
    
    # Another upcoming tournament
    upcoming_tournament2 = Tournament(
        name="Pacific Northwest Open",
        organizer_id=organizer.id,
        location="Seattle, Washington",
        description="Bringing together the best pickleball talent from the Pacific Northwest and beyond.",
        start_date=datetime.utcnow() + timedelta(days=60),
        end_date=datetime.utcnow() + timedelta(days=63),
        registration_deadline=datetime.utcnow() + timedelta(days=45),
        tier=TournamentTier.SLATE,
        format=TournamentFormat.GROUP_KNOCKOUT,
        status=TournamentStatus.UPCOMING,
        prize_pool=50000.0,
        registration_fee=250.0
    )
    db.session.add(upcoming_tournament2)
    tournaments.append(upcoming_tournament2)
    
    db.session.commit()
    
    return tournaments

def seed_categories(tournaments):
    print("Seeding tournament categories...")
    # Check if categories already exist
    if TournamentCategory.query.count() > 0:
        print("Tournament categories already exist, skipping...")
        return TournamentCategory.query.all()
    
    categories = []
    
    for tournament in tournaments:
        # Points based on tournament tier
        if tournament.tier == TournamentTier.SLATE:
            points = 2000
        elif tournament.tier == TournamentTier.CUP:
            points = 3200
        elif tournament.tier == TournamentTier.OPEN:
            points = 1400
        else:  # CHALLENGE
            points = 925
            
        # Add categories
        mens_singles = TournamentCategory(
            tournament_id=tournament.id,
            category_type=CategoryType.MENS_SINGLES,
            max_participants=32,
            points_awarded=points
        )
        db.session.add(mens_singles)
        categories.append(mens_singles)
        
        womens_singles = TournamentCategory(
            tournament_id=tournament.id,
            category_type=CategoryType.WOMENS_SINGLES,
            max_participants=32,
            points_awarded=points
        )
        db.session.add(womens_singles)
        categories.append(womens_singles)
        
        mens_doubles = TournamentCategory(
            tournament_id=tournament.id,
            category_type=CategoryType.MENS_DOUBLES,
            max_participants=24,
            points_awarded=points
        )
        db.session.add(mens_doubles)
        categories.append(mens_doubles)
        
        womens_doubles = TournamentCategory(
            tournament_id=tournament.id,
            category_type=CategoryType.WOMENS_DOUBLES,
            max_participants=24,
            points_awarded=points
        )
        db.session.add(womens_doubles)
        categories.append(womens_doubles)
        
        mixed_doubles = TournamentCategory(
            tournament_id=tournament.id,
            category_type=CategoryType.MIXED_DOUBLES,
            max_participants=32,
            points_awarded=points
        )
        db.session.add(mixed_doubles)
        categories.append(mixed_doubles)
    
    db.session.commit()
    
    return categories

def seed_registrations(player_profiles, categories):
    print("Seeding registrations...")
    # Check if registrations already exist
    if Registration.query.count() > 0:
        print("Registrations already exist, skipping...")
        return Registration.query.all()
    
    registrations = []
    teams = []
    
    # For each tournament category, register some players
    for category in categories:
        # Get tournament
        tournament = Tournament.query.get(category.tournament_id)
        
        # Determine if this is a doubles category
        is_doubles = category.category_type in [
            CategoryType.MENS_DOUBLES, 
            CategoryType.WOMENS_DOUBLES, 
            CategoryType.MIXED_DOUBLES
        ]
        
        # Get players who can register for this category based on gender
        eligible_players = []
        if category.category_type in [CategoryType.MENS_SINGLES, CategoryType.MENS_DOUBLES]:
            eligible_players = [p for p in player_profiles if p.mens_singles_points > 0 or p.mens_doubles_points > 0]
        elif category.category_type in [CategoryType.WOMENS_SINGLES, CategoryType.WOMENS_DOUBLES]:
            eligible_players = [p for p in player_profiles if p.womens_singles_points > 0 or p.womens_doubles_points > 0]
        else:  # Mixed doubles
            eligible_players = player_profiles
        
        # Skip if no eligible players
        if not eligible_players:
            continue
            
        # Register 8-16 players for each category
        num_registrations = min(len(eligible_players), random.randint(8, 16))
        # Ensure even number for doubles
        if is_doubles and num_registrations % 2 == 1:
            num_registrations -= 1
            
        selected_players = random.sample(eligible_players, num_registrations)
        
        # For doubles, we'll create teams
        if is_doubles:
            # Create pairs of players
            for i in range(0, len(selected_players), 2):
                if i + 1 < len(selected_players):
                    player1 = selected_players[i]
                    player2 = selected_players[i+1]
                    
                    # Create registration for first player
                    reg1 = Registration(
                        player_id=player1.id,
                        category_id=category.id,
                        partner_id=player2.id,
                        registration_date=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
                        is_approved=True,
                        seed=i//2 + 1 if i//2 < 4 else None,  # Seed top 4 teams
                        payment_status='paid'
                    )
                    db.session.add(reg1)
                    registrations.append(reg1)
                    
                    # Create registration for second player
                    reg2 = Registration(
                        player_id=player2.id,
                        category_id=category.id,
                        partner_id=player1.id,
                        registration_date=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
                        is_approved=True,
                        seed=i//2 + 1 if i//2 < 4 else None,  # Same seed as partner
                        payment_status='paid'
                    )
                    db.session.add(reg2)
                    registrations.append(reg2)
                    
                    # Create a team for this pair
                    team = Team(
                        player1_id=player1.id,
                        player2_id=player2.id,
                        category_id=category.id
                    )
                    db.session.add(team)
                    teams.append(team)
        else:
            # Singles - register individual players
            for i, player in enumerate(selected_players):
                reg = Registration(
                    player_id=player.id,
                    category_id=category.id,
                    registration_date=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
                    is_approved=True,
                    seed=i + 1 if i < 8 else None,  # Seed top 8 players
                    payment_status='paid'
                )
                db.session.add(reg)
                registrations.append(reg)
    
    db.session.commit()
    
    return registrations, teams

def create_tournament_bracket(category, registrations, is_doubles=False):
    """
    Create a tournament bracket for a category with proper progression and BYE handling
    
    Args:
        category: TournamentCategory object
        registrations: List of Registration objects for this category
        is_doubles: Boolean indicating if this is a doubles category
    
    Returns:
        List of created Match objects
    """
    print(f"Creating bracket for {category.category_type.value} with {len(registrations)} registrations")
    
    # Get tournament
    tournament = Tournament.query.get(category.tournament_id)
    all_matches = []
    
    # Determine bracket size (power of 2)
    num_participants = len(registrations)
    bracket_size = 1
    while bracket_size < num_participants:
        bracket_size *= 2
        
    # Calculate number of rounds
    num_rounds = 0
    temp = bracket_size
    while temp > 1:
        temp //= 2
        num_rounds += 1
        
    print(f"Bracket size: {bracket_size}, Rounds: {num_rounds}")
    
    # For doubles, create teams first
    teams = []
    players_by_id = {}
    
    if is_doubles:
        # Group registrations by team (using partner_id)
        team_groups = {}
        for reg in registrations:
            player = PlayerProfile.query.get(reg.player_id)
            players_by_id[player.id] = player
            
            # Create a unique key for this team (using sorted IDs to avoid duplicates)
            team_key = tuple(sorted([reg.player_id, reg.partner_id]))
            
            if team_key not in team_groups:
                team_groups[team_key] = [reg]
            else:
                team_groups[team_key].append(reg)
        
        # Create Team objects for each unique team
        for team_key, regs in team_groups.items():
            if len(regs) > 0:
                reg = regs[0]  # Use the first registration to create the team
                
                # Skip if partner doesn't exist
                if not reg.partner_id:
                    continue
                    
                # Get players
                player1 = PlayerProfile.query.get(reg.player_id)
                player2 = PlayerProfile.query.get(reg.partner_id)
                
                if player1 and player2:
                    team = Team(
                        player1_id=player1.id,
                        player2_id=player2.id,
                        category_id=category.id
                    )
                    db.session.add(team)
                    # We need to flush to get the team ID
                    db.session.flush()
                    teams.append(team)
                    
        print(f"Created {len(teams)} teams for doubles category")
        # Use teams as participants
        participants = teams
    else:
        # Use players directly for singles
        participants = []
        for reg in registrations:
            player = PlayerProfile.query.get(reg.player_id)
            if player:
                participants.append(player)
                players_by_id[player.id] = player
    
    # Create a seeded list with BYEs in correct positions
    seeded_participants = [None] * bracket_size
    
    # Place participants based on seeding (simple implementation)
    for i, participant in enumerate(participants):
        if i < bracket_size:
            # Simple seeding: 1, bracket_size, bracket_size/2, bracket_size*3/4, etc.
            if i == 0:
                seeded_participants[0] = participant  # 1 seed
            elif i == 1:
                seeded_participants[bracket_size - 1] = participant  # 2 seed
            elif i == 2:
                seeded_participants[bracket_size // 2] = participant  # 3 seed
            elif i == 3:
                seeded_participants[bracket_size // 4] = participant  # 4 seed
            else:
                # Find the first empty slot
                for j in range(bracket_size):
                    if seeded_participants[j] is None:
                        seeded_participants[j] = participant
                        break
    
    # Create matches for each round, starting from first round
    rounds = {}
    
    # First round - match players against each other with BYEs
    first_round_matches = []
    for i in range(0, bracket_size, 2):
        participant1 = seeded_participants[i]
        participant2 = seeded_participants[i + 1]
        
        if is_doubles:
            # Create a doubles match
            match = Match(
                category_id=category.id,
                round=num_rounds,
                match_order=i // 2,
                team1_id=participant1.id if participant1 else None,
                team2_id=participant2.id if participant2 else None,
                court=f"Court {random.randint(1, 8)}",
                scheduled_time=tournament.start_date + timedelta(hours=random.randint(0, 48))
            )
        else:
            # Create a singles match
            match = Match(
                category_id=category.id,
                round=num_rounds,
                match_order=i // 2,
                player1_id=participant1.id if participant1 else None,
                player2_id=participant2.id if participant2 else None,
                court=f"Court {random.randint(1, 8)}",
                scheduled_time=tournament.start_date + timedelta(hours=random.randint(0, 48))
            )
        
        db.session.add(match)
        first_round_matches.append(match)
        all_matches.append(match)
    
    rounds[num_rounds] = first_round_matches
    
    # Create empty matches for subsequent rounds
    for round_num in range(num_rounds - 1, 0, -1):
        matches_in_round = 2 ** (round_num - 1)
        round_matches = []
        
        for i in range(matches_in_round):
            match = Match(
                category_id=category.id,
                round=round_num,
                match_order=i,
                court=f"Court {random.randint(1, 8)}",
                scheduled_time=tournament.start_date + timedelta(hours=random.randint(24, 72))
            )
            db.session.add(match)
            round_matches.append(match)
            all_matches.append(match)
        
        rounds[round_num] = round_matches
    
    # Commit to get match IDs
    db.session.flush()
    
    # Link matches - set next_match_id
    for round_num in range(num_rounds, 1, -1):
        for i, match in enumerate(rounds[round_num]):
            next_round = round_num - 1
            next_match_idx = i // 2
            match.next_match_id = rounds[next_round][next_match_idx].id
    
    # For completed tournaments, fill in results and advance winners
    if tournament.status == TournamentStatus.COMPLETED:
        # Process first round with BYEs
        for match in first_round_matches:
            match.completed = True
            
            if is_doubles:
                # Doubles match
                if match.team1_id and match.team2_id:
                    # Both teams present - randomly pick winner
                    if random.random() > 0.5:
                        match.winning_team_id = match.team1_id
                        match.losing_team_id = match.team2_id
                    else:
                        match.winning_team_id = match.team2_id
                        match.losing_team_id = match.team1_id
                elif match.team1_id:
                    # Team 1 vs BYE
                    match.winning_team_id = match.team1_id
                elif match.team2_id:
                    # Team 2 vs BYE
                    match.winning_team_id = match.team2_id
            else:
                # Singles match
                if match.player1_id and match.player2_id:
                    # Both players present - randomly pick winner
                    if random.random() > 0.5:
                        match.winning_player_id = match.player1_id
                        match.losing_player_id = match.player2_id
                    else:
                        match.winning_player_id = match.player2_id
                        match.losing_player_id = match.player1_id
                elif match.player1_id:
                    # Player 1 vs BYE
                    match.winning_player_id = match.player1_id
                elif match.player2_id:
                    # Player 2 vs BYE
                    match.winning_player_id = match.player2_id
            
            # Add scores for non-BYE matches
            if (is_doubles and match.team1_id and match.team2_id) or \
               (not is_doubles and match.player1_id and match.player2_id):
                # Add 2-3 sets
                sets = random.randint(2, 3)
                for set_num in range(1, sets + 1):
                    # Determine who won this set
                    if is_doubles:
                        winner_is_team1 = match.winning_team_id == match.team1_id
                    else:
                        winner_is_player1 = match.winning_player_id == match.player1_id
                    
                    # First two sets are to 11
                    if set_num <= 2:
                        if (is_doubles and winner_is_team1) or (not is_doubles and winner_is_player1):
                            score1 = 11
                            score2 = random.randint(4, 9)
                        else:
                            score1 = random.randint(4, 9)
                            score2 = 11
                    # Third set is to 15
                    else:
                        if (is_doubles and winner_is_team1) or (not is_doubles and winner_is_player1):
                            score1 = 15
                            score2 = random.randint(10, 13)
                        else:
                            score1 = random.randint(10, 13)
                            score2 = 15
                    
                    # Create score
                    score = MatchScore(
                        match_id=match.id,
                        set_number=set_num,
                        player1_score=score1,
                        player2_score=score2
                    )
                    db.session.add(score)
            
            # Advance winner to next match if there is one
            if match.next_match_id:
                next_match = next((m for m in all_matches if m.id == match.next_match_id), None)
                if next_match:
                    # Determine if winner goes to player1/team1 or player2/team2 position
                    is_left_bracket = match.match_order % 2 == 0
                    
                    if is_doubles:
                        if match.winning_team_id:
                            if is_left_bracket:
                                next_match.team1_id = match.winning_team_id
                            else:
                                next_match.team2_id = match.winning_team_id
                    else:
                        if match.winning_player_id:
                            if is_left_bracket:
                                next_match.player1_id = match.winning_player_id
                            else:
                                next_match.player2_id = match.winning_player_id
        
        # Process subsequent rounds
        for round_num in range(num_rounds - 1, 0, -1):
            for match in rounds[round_num]:
                match.completed = True
                
                if is_doubles:
                    # Doubles match
                    if match.team1_id and match.team2_id:
                        # Randomly pick winner
                        if random.random() > 0.5:
                            match.winning_team_id = match.team1_id
                            match.losing_team_id = match.team2_id
                        else:
                            match.winning_team_id = match.team2_id
                            match.losing_team_id = match.team1_id
                    elif match.team1_id:
                        match.winning_team_id = match.team1_id
                    elif match.team2_id:
                        match.winning_team_id = match.team2_id
                else:
                    # Singles match
                    if match.player1_id and match.player2_id:
                        # Randomly pick winner
                        if random.random() > 0.5:
                            match.winning_player_id = match.player1_id
                            match.losing_player_id = match.player2_id
                        else:
                            match.winning_player_id = match.player2_id
                            match.losing_player_id = match.player1_id
                    elif match.player1_id:
                        match.winning_player_id = match.player1_id
                    elif match.player2_id:
                        match.winning_player_id = match.player2_id
                
                # Add scores if both players/teams are present
                if (is_doubles and match.team1_id and match.team2_id) or \
                   (not is_doubles and match.player1_id and match.player2_id):
                    # Add 2-3 sets
                    sets = random.randint(2, 3)
                    for set_num in range(1, sets + 1):
                        # Determine who won this set
                        if is_doubles:
                            winner_is_team1 = match.winning_team_id == match.team1_id
                        else:
                            winner_is_player1 = match.winning_player_id == match.player1_id
                        
                        # First two sets are to 11
                        if set_num <= 2:
                            if (is_doubles and winner_is_team1) or (not is_doubles and winner_is_player1):
                                score1 = 11
                                score2 = random.randint(4, 9)
                            else:
                                score1 = random.randint(4, 9)
                                score2 = 11
                        # Third set is to 15
                        else:
                            if (is_doubles and winner_is_team1) or (not is_doubles and winner_is_player1):
                                score1 = 15
                                score2 = random.randint(10, 13)
                            else:
                                score1 = random.randint(10, 13)
                                score2 = 15
                        
                        # Create score
                        score = MatchScore(
                            match_id=match.id,
                            set_number=set_num,
                            player1_score=score1,
                            player2_score=score2
                        )
                        db.session.add(score)
                
                # Advance winner to next match if there is one
                if match.next_match_id:
                    next_match = next((m for m in all_matches if m.id == match.next_match_id), None)
                    if next_match:
                        # Determine if winner goes to player1/team1 or player2/team2 position
                        is_left_bracket = match.match_order % 2 == 0
                        
                        if is_doubles:
                            if match.winning_team_id:
                                if is_left_bracket:
                                    next_match.team1_id = match.winning_team_id
                                else:
                                    next_match.team2_id = match.winning_team_id
                        else:
                            if match.winning_player_id:
                                if is_left_bracket:
                                    next_match.player1_id = match.winning_player_id
                                else:
                                    next_match.player2_id = match.winning_player_id
    
    # For ongoing tournaments, only complete some matches
    elif tournament.status == TournamentStatus.ONGOING:
        # Complete first 2 rounds only
        rounds_to_complete = min(2, num_rounds)
        
        for round_num in range(num_rounds, num_rounds - rounds_to_complete, -1):
            for match in rounds[round_num]:
                match.completed = True
                
                # Same logic as above for determining winners
                if is_doubles:
                    # Doubles match
                    if match.team1_id and match.team2_id:
                        # Randomly pick winner
                        if random.random() > 0.5:
                            match.winning_team_id = match.team1_id
                            match.losing_team_id = match.team2_id
                        else:
                            match.winning_team_id = match.team2_id
                            match.losing_team_id = match.team1_id
                    elif match.team1_id:
                        match.winning_team_id = match.team1_id
                    elif match.team2_id:
                        match.winning_team_id = match.team2_id
                else:
                    # Singles match
                    if match.player1_id and match.player2_id:
                        # Randomly pick winner
                        if random.random() > 0.5:
                            match.winning_player_id = match.player1_id
                            match.losing_player_id = match.player2_id
                        else:
                            match.winning_player_id = match.player2_id
                            match.losing_player_id = match.player1_id
                    elif match.player1_id:
                        match.winning_player_id = match.player1_id
                    elif match.player2_id:
                        match.winning_player_id = match.player2_id
                
                # Add scores
                if (is_doubles and match.team1_id and match.team2_id) or \
                   (not is_doubles and match.player1_id and match.player2_id):
                    # Add scores as above
                    sets = random.randint(2, 3)
                    for set_num in range(1, sets + 1):
                        # Same score logic as the completed tournament case
                        if is_doubles:
                            winner_is_team1 = match.winning_team_id == match.team1_id
                        else:
                            winner_is_player1 = match.winning_player_id == match.player1_id
                        
                        if set_num <= 2:
                            if (is_doubles and winner_is_team1) or (not is_doubles and winner_is_player1):
                                score1 = 11
                                score2 = random.randint(4, 9)
                            else:
                                score1 = random.randint(4, 9)
                                score2 = 11
                        else:
                            if (is_doubles and winner_is_team1) or (not is_doubles and winner_is_player1):
                                score1 = 15
                                score2 = random.randint(10, 13)
                            else:
                                score1 = random.randint(10, 13)
                                score2 = 15
                        
                        score = MatchScore(
                            match_id=match.id,
                            set_number=set_num,
                            player1_score=score1,
                            player2_score=score2
                        )
                        db.session.add(score)
                
                # Advance winners for completed matches
                if match.next_match_id:
                    next_match = next((m for m in all_matches if m.id == match.next_match_id), None)
                    if next_match:
                        is_left_bracket = match.match_order % 2 == 0
                        
                        if is_doubles:
                            if match.winning_team_id:
                                if is_left_bracket:
                                    next_match.team1_id = match.winning_team_id
                                else:
                                    next_match.team2_id = match.winning_team_id
                        else:
                            if match.winning_player_id:
                                if is_left_bracket:
                                    next_match.player1_id = match.winning_player_id
                                else:
                                    next_match.player2_id = match.winning_player_id
    
    return all_matches

def seed_matches(categories, teams):
    print("Seeding matches...")
    # Check if matches already exist
    if Match.query.count() > 0:
        print("Matches already exist, skipping...")
        return Match.query.all()
    
    all_matches = []
    
    # Only generate matches for past and current tournaments
    for category in categories:
        tournament = Tournament.query.get(category.tournament_id)
        if tournament.status == TournamentStatus.UPCOMING:
            continue
            
        # Determine if this is a doubles category
        is_doubles = category.category_type in [
            CategoryType.MENS_DOUBLES, 
            CategoryType.WOMENS_DOUBLES, 
            CategoryType.MIXED_DOUBLES
        ]
        
        # Get registrations for this category
        registrations = Registration.query.filter_by(category_id=category.id).all()
        if len(registrations) < 2:
            print(f"Skipping {category.category_type.value} - not enough registrations")
            continue
        
        print(f"Creating bracket for {tournament.name} - {category.category_type.value}")
        
        # Use our improved bracket creation function
        category_matches = create_tournament_bracket(category, registrations, is_doubles)
        all_matches.extend(category_matches)
    
    # Commit all changes
    db.session.commit()
    
    # Verify our bracket creation
    verify_brackets(categories)
    
    return all_matches

def verify_brackets(categories):
    """Verify that all brackets are properly set up"""
    print("\nVerifying brackets...")
    
    for category in categories:
        tournament = Tournament.query.get(category.tournament_id)
        if tournament.status != TournamentStatus.COMPLETED:
            continue
            
        print(f"Checking {tournament.name} - {category.category_type.value}")
        
        # Get all matches for this category
        matches = Match.query.filter_by(category_id=category.id).order_by(Match.round).all()
        
        # Check final match
        final_matches = [m for m in matches if m.round == 1]
        if not final_matches:
            print(f"  - WARNING: No final match found!")
            continue
            
        final_match = final_matches[0]
        
        # Determine if this is a doubles category
        is_doubles = category.category_type in [
            CategoryType.MENS_DOUBLES, 
            CategoryType.WOMENS_DOUBLES, 
            CategoryType.MIXED_DOUBLES
        ]
        
        if is_doubles:
            # Check teams and winners
            if final_match.team1_id or final_match.team2_id:
                if final_match.winning_team_id:
                    winning_team = Team.query.get(final_match.winning_team_id)
                    player1 = PlayerProfile.query.get(winning_team.player1_id)
                    player2 = PlayerProfile.query.get(winning_team.player2_id)
                    print(f"  - Winner team: {player1.full_name} & {player2.full_name}")
                else:
                    print(f"  - WARNING: Final match has players but no winner!")
            else:
                print(f"  - WARNING: Final match has no teams!")
        else:
            # Check players and winners
            if final_match.player1_id or final_match.player2_id:
                if final_match.winning_player_id:
                    winner = PlayerProfile.query.get(final_match.winning_player_id)
                    print(f"  - Winner: {winner.full_name}")
                else:
                    print(f"  - WARNING: Final match has players but no winner!")
            else:
                print(f"  - WARNING: Final match has no players!")
        
        # Count matches with missing data
        incomplete_matches = 0
        for match in matches:
            if match.completed:
                if is_doubles:
                    if not (match.team1_id or match.team2_id):
                        incomplete_matches += 1
                    elif not match.winning_team_id:
                        incomplete_matches += 1
                else:
                    if not (match.player1_id or match.player2_id):
                        incomplete_matches += 1
                    elif not match.winning_player_id:
                        incomplete_matches += 1
        
        if incomplete_matches > 0:
            print(f"  - WARNING: {incomplete_matches} completed matches with missing data!")

def seed_equipment_and_sponsors(player_profiles):
    print("Seeding equipment and sponsors...")
    # Check if equipment already exists
    if Equipment.query.count() > 0:
        print("Equipment already exists, skipping...")
        return
    
    brands = [
        "ProKennex", "Selkirk", "Paddletek", "Engage", "Onix", "Head", "Gamma", 
        "Franklin", "Wilson", "Vulcan", "Babolat", "Prince", "Joola"
    ]
    
    sponsor_names = [
        "Pickleball Central", "Dura Fast 40", "Jigsaw Health", "DUPR", 
        "USA Pickleball", "Fruit2O", "Takeya", "Franklin", "Electrum", 
        "Pickleball Magazine", "The Dink", "TMPR", "ChampionWear"
    ]
    
    for profile in player_profiles:
        # Add 1-3 equipment items
        num_equipment = random.randint(1, 3)
        for _ in range(num_equipment):
            brand = random.choice(brands)
            equipment_type = random.choice(["Paddle", "Shoes", "Apparel"])
            
            equipment = Equipment(
                player_id=profile.id,
                brand=brand,
                name=f"{brand} {['Pro', 'Elite', 'Tour', 'Master', 'Champion'][random.randint(0, 4)]} {equipment_type}",
                buy_link=f"https://example.com/shop/{brand.lower()}"
            )
            db.session.add(equipment)
        
        # Add 0-2 sponsors
        num_sponsors = random.randint(0, 2)
        for _ in range(num_sponsors):
            sponsor_name = random.choice(sponsor_names)
            
            sponsor = Sponsor(
                player_id=profile.id,
                name=sponsor_name,
                link=f"https://{sponsor_name.lower().replace(' ', '')}.com"
            )
            db.session.add(sponsor)
    
    db.session.commit()

def seed_database():
    print("\nStarting database seeding...")
    admin, organizer, players = seed_users()
    player_profiles = seed_player_profiles(players)
    tournaments = seed_tournaments(organizer)
    categories = seed_categories(tournaments)
    registrations, teams = seed_registrations(player_profiles, categories)
    matches = seed_matches(categories, teams)
    seed_equipment_and_sponsors(player_profiles)
    
    print("\nDatabase seeding completed successfully!")

if __name__ == "__main__":
    # Create app context for database operations
    app = create_app()
    with app.app_context():
        seed_database()