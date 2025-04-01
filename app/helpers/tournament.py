# Helper Functions
from flask import current_app
from app import db
from app.models import Registration, Match, MatchStage, Team, PlayerProfile, Group, GroupStanding

def _format_match_for_api(match):
    """Helper to format match data for API responses"""
    match_info = {
        'id': match.id,
        'round': match.round,
        'round_name': match.round_name if hasattr(match, 'round_name') else f"Round {match.round}",
        'match_order': match.match_order,
        'completed': match.completed,
        'scores': []
    }
    
    # Add participant info
    if hasattr(match, 'is_doubles') and match.is_doubles:
        # Doubles match
        if match.team1:
            match_info['team1_name'] = f"{match.team1.player1.full_name}/{match.team1.player2.full_name}"
            match_info['team1_id'] = match.team1_id
        else:
            # Use position code if available, otherwise TBD
            match_info['team1_name'] = match.player1_code if match.player1_code else "TBD"
            match_info['team1_id'] = None
        
        if match.team2:
            match_info['team2_name'] = f"{match.team2.player1.full_name}/{match.team2.player2.full_name}"
            match_info['team2_id'] = match.team2_id
        else:
            # Use position code if available, otherwise TBD
            match_info['team2_name'] = match.player2_code if match.player2_code else "TBD"
            match_info['team2_id'] = None
        
        if hasattr(match, 'winner') and match.winner:
            match_info['winner_name'] = f"{match.winner.player1.full_name}/{match.winner.player2.full_name}"
            match_info['winner_id'] = match.winner_id
    else:
        # Singles match
        if match.player1:
            match_info['player1_name'] = match.player1.full_name
            match_info['player1_id'] = match.player1_id
        else:
            # Use position code if available, otherwise TBD
            match_info['player1_name'] = match.player1_code if match.player1_code else "TBD"
            match_info['player1_id'] = None
        
        if match.player2:
            match_info['player2_name'] = match.player2.full_name
            match_info['player2_id'] = match.player2_id
        else:
            # Use position code if available, otherwise TBD
            match_info['player2_name'] = match.player2_code if match.player2_code else "TBD"
            match_info['player2_id'] = None
        
        if hasattr(match, 'winner') and match.winner:
            match_info['winner_name'] = match.winner.full_name
            match_info['winner_id'] = match.winner_id
    
    # Add codes if available
    if hasattr(match, 'player1_code') and match.player1_code:
        match_info['player1_code'] = match.player1_code
    if hasattr(match, 'player2_code') and match.player2_code:
        match_info['player2_code'] = match.player2_code
    
    # Add scores
    if hasattr(match, 'player1_code') and match.player1_code:
        match_info['player1_code'] = match.player1_code
    if hasattr(match, 'player2_code') and match.player2_code:
        match_info['player2_code'] = match.player2_code

    for score in match.scores:
        match_info['scores'].append({
            'player1_score': score.player1_score,
            'player2_score': score.player2_score
        })
    
    # Add scheduling info if available
    if match.scheduled_time:
        match_info['scheduled_time'] = match.scheduled_time.strftime('%Y-%m-%d %H:%M')
    
    if match.court:
        match_info['court'] = match.court
        
    # Add verification info
    match_info['referee_verified'] = match.referee_verified
    match_info['player_verified'] = match.player_verified
    
    # Add livestream URL if available
    if match.livestream_url:
        match_info['livestream_url'] = match.livestream_url
    
    return match_info

def _generate_group_stage(category):
    """Generate group stage matches for a category"""
    if not category.group_count:
        category.group_count = 4  # Default to 4 groups
    if not category.teams_per_group:
        # Calculate teams per group if not specified
        registrations_count = Registration.query.filter_by(category_id=category.id, is_approved=True).count()
        if registrations_count > 0 and category.group_count > 0:
            category.teams_per_group = (registrations_count + category.group_count - 1) // category.group_count
        else:
            category.teams_per_group = 4  # Default to 4 teams per group
    
    # Get registrations
    registrations = Registration.query.filter_by(category_id=category.id, is_approved=True).all()
    if len(registrations) < category.group_count * 2:  # Need at least 2 teams per group
        return False
    
    # Clear existing groups and group matches
    group_ids = [g.id for g in Group.query.filter_by(category_id=category.id).all()]
    Match.query.filter(Match.group_id.in_(group_ids)).delete(synchronize_session=False)
    GroupStanding.query.filter(GroupStanding.group_id.in_(group_ids)).delete(synchronize_session=False)
    Group.query.filter_by(category_id=category.id).delete(synchronize_session=False)
    
    # Create groups
    groups = []
    for i in range(category.group_count):
        group = Group(
            category_id=category.id,
            name=chr(65 + i)  # A, B, C, etc.
        )
        db.session.add(group)
        db.session.flush()  # Get the group ID
        groups.append(group)
    
    # Sort by seed if available
    sorted_regs = sorted(registrations, key=lambda x: x.seed if x.seed is not None else 999)
    
    # Create participants list (either teams or players)
    participants = []
    is_doubles = category.is_doubles()
    
    if is_doubles:
        # Create teams
        for reg in sorted_regs:
            if reg.partner_id:
                team = Team.query.filter_by(
                    player1_id=reg.player_id,
                    player2_id=reg.partner_id,
                    category_id=category.id
                ).first()
                
                if not team:
                    team = Team(
                        player1_id=reg.player_id,
                        player2_id=reg.partner_id,
                        category_id=category.id
                    )
                    db.session.add(team)
                    db.session.flush()
                
                participants.append(team)
    else:
        # Singles players
        for reg in sorted_regs:
            player = PlayerProfile.query.get(reg.player_id)
            participants.append(player)
    
    # Distribute participants to groups using snake seeding
    group_participants = [[] for _ in range(len(groups))]
    
    for i, participant in enumerate(participants):
        group_index = i % len(groups)
        # Reverse direction on even passes
        if (i // len(groups)) % 2 == 1:
            group_index = len(groups) - 1 - group_index
        
        group_participants[group_index].append(participant)
    
    # Create group standings and matches
    for i, group in enumerate(groups):
        # Create standings with position codes
        for j, participant in enumerate(group_participants[i]):
            # Create position code based on group name and position (e.g., A1, B2)
            position_code = f"{group.name}{j+1}"
            
            standing = GroupStanding(group_id=group.id)
            
            if is_doubles:
                standing.team_id = participant.id
            else:
                standing.player_id = participant.id
            
            # Store the initial position in the standings (1-based)
            standing.position = j + 1
            
            db.session.add(standing)
        
        # Create round-robin matches with position codes
        _create_round_robin_matches(group, group_participants[i], is_doubles)
    
    db.session.commit()
    return True

def _create_round_robin_matches(group, participants, is_doubles):
    """Create round-robin matches for a group"""
    n = len(participants)
    if n < 2:
        return
    
    # Round robin scheduling algorithm
    matches = []
    
    if n % 2 == 1:
        # Add a dummy participant for odd number
        participants.append(None)
        n += 1
    
    # Generate rounds
    for round_num in range(n - 1):
        for i in range(n // 2):
            team1 = participants[i]
            team2 = participants[n - 1 - i]
            
            if team1 is not None and team2 is not None:
                match = Match(
                    category_id=group.category_id,
                    group_id=group.id,
                    stage=MatchStage.GROUP,
                    round=round_num + 1,
                    match_order=(round_num * 10) + i  # Ensures unique ordering
                )
                
                # Assign player/team IDs
                if is_doubles:
                    match.team1_id = team1.id
                    match.team2_id = team2.id
                else:
                    match.player1_id = team1.id
                    match.player2_id = team2.id
                
                # Assign position codes based on group and index
                # Get index of participants in the group for position codes
                team1_index = participants.index(team1)
                team2_index = participants.index(team2)
                
                # Create position codes (e.g., A1, B2)
                match.player1_code = f"{group.name}{team1_index+1}"
                match.player2_code = f"{group.name}{team2_index+1}"
                
                db.session.add(match)
        
        # Rotate participants (keep first participant fixed)
        participants = [participants[0]] + [participants[-1]] + participants[1:-1]
    
    db.session.flush()

def _generate_knockout_from_groups(category):
    """Generate knockout stage based on group results"""

    
    # Ensure groups exist
    groups = Group.query.filter_by(category_id=category.id).all()
    if not groups or len(groups) < 2:
        return False
    
    # Get advancing teams from each group
    advancing_participants = []
    is_doubles = category.is_doubles()
    
    group_stage_complete = True
    for group in groups:
        # Check if all group matches are completed
        group_matches = Match.query.filter_by(
            group_id=group.id, 
            stage=MatchStage.GROUP
        ).all()
        
        # If no matches or any match is not completed, group stage isn't complete
        if not group_matches or any(not m.completed for m in group_matches):
            group_stage_complete = False
            break

    if group_stage_complete:
        # Use actual standings if group stage is complete
        for group in groups:
            standings = GroupStanding.query.filter_by(group_id=group.id)\
                .order_by(GroupStanding.position).limit(category.teams_advancing_per_group).all()
        
            for standing in standings:
                if is_doubles:
                    advancing_participants.append({
                        'team': standing.team,
                        'group': group.name,
                        'position': standing.position,
                        'code': f"{group.name}{standing.position}"  # Position code (e.g., A1, B2)
                    })
                else:
                    advancing_participants.append({
                        'player': standing.player,
                        'group': group.name,
                        'position': standing.position,
                        'code': f"{group.name}{standing.position}"  # Position code (e.g., A1, B2)
                    })
    else:
        # Create placeholder participants with codes if group stage not complete
        for group in groups:
            for pos in range(1, category.teams_advancing_per_group + 1):
                code = f"{group.name}{pos}"
                advancing_participants.append({
                    'team': None if is_doubles else None,
                    'player': None if not is_doubles else None,
                    'group': group.name,
                    'position': pos,
                    'code': code
                })
    
    # Clear existing knockout matches
    Match.query.filter_by(
        category_id=category.id, 
        stage=MatchStage.KNOCKOUT
    ).delete(synchronize_session=False)
    
    # Determine bracket size (next power of 2)
    bracket_size = 1
    while bracket_size < len(advancing_participants):
        bracket_size *= 2
    
    # Generate seeding based on group results
    # Top teams from each group are seeded, then second place, etc.
    seeded_participants = []
    
    # Sort by position first, then by group
    sorted_participants = sorted(
        advancing_participants,
        key=lambda p: (p['position'], p['group'])
    )
    
    # Add sorted participants to seeded list
    seeded_participants.extend(sorted_participants)
    
    # Add byes to fill bracket
    while len(seeded_participants) < bracket_size:
        seeded_participants.append(None)
    
    # Generate knockout matches with codes
    _create_knockout_matches(category, seeded_participants, is_doubles)
    
    db.session.commit()
    return True

def _generate_single_elimination(category, use_seeding=True, third_place_match=True):
    """Generate single elimination bracket from registrations"""
    # Get registrations
    registrations = Registration.query.filter_by(category_id=category.id, is_approved=True).all()
    if not registrations:
        return False
    
    # Clear existing knockout matches
    Match.query.filter_by(category_id=category.id).delete(synchronize_session=False)
    
    # Create participants list (either teams or players)
    participants = []
    is_doubles = category.is_doubles()
    
    if is_doubles:
        # Create teams from registrations
        for reg in registrations:
            if reg.partner_id:
                team = Team.query.filter_by(
                    player1_id=reg.player_id,
                    player2_id=reg.partner_id,
                    category_id=category.id
                ).first()
                
                if not team:
                    team = Team(
                        player1_id=reg.player_id,
                        player2_id=reg.partner_id,
                        category_id=category.id
                    )
                    db.session.add(team)
                    db.session.flush()
                
                participants.append({
                    'team': team,
                    'seed': reg.seed
                })
    else:
        # Singles players
        for reg in registrations:
            player = PlayerProfile.query.get(reg.player_id)
            participants.append({
                'player': player,
                'seed': reg.seed
            })
    
    # Sort by seed if available and seeding is enabled
    seeded_participants = []
    if use_seeding:
        sorted_participants = sorted(
            participants,
            key=lambda p: p['seed'] if p['seed'] is not None else 999
        )
        
        # Extract just the player/team from each entry
        for p in sorted_participants:
            if is_doubles:
                seeded_participants.append({
                    'participant': p['team'],
                    'code': f"S{p['seed']}" if p['seed'] is not None else None  # Add seed code
                })
            else:
                seeded_participants.append({
                    'participant': p['player'],
                    'code': f"S{p['seed']}" if p['seed'] is not None else None  # Add seed code
                })
    else:
        # No seeding, just extract players/teams
        for i, p in enumerate(participants):
            if is_doubles:
                seeded_participants.append({
                    'participant': p['team'],
                    'code': f"P{i+1}"  # Player/team number as code
                })
            else:
                seeded_participants.append({
                    'participant': p['player'],
                    'code': f"P{i+1}"  # Player/team number as code
                })
    
    # Determine bracket size (next power of 2)
    bracket_size = 1
    while bracket_size < len(seeded_participants):
        bracket_size *= 2
    
    # Add byes to fill bracket
    while len(seeded_participants) < bracket_size:
        seeded_participants.append(None)
    
    # Generate knockout matches
    _create_knockout_matches(category, seeded_participants, is_doubles, third_place_match)
    
    db.session.commit()
    return True

def _create_knockout_matches(category, seeded_participants, is_doubles, third_place_match=True):
    """Create knockout bracket matches based on seeded participants"""
    n = len(seeded_participants)
    if n < 2:
        return
    
    # Determine number of rounds
    round_count = 0
    temp = n
    while temp > 1:
        temp //= 2
        round_count += 1
    
    # Create matches for first round
    first_round = round_count
    matches = []
    
    for i in range(0, n, 2):
        match = Match(
            category_id=category.id,
            stage=MatchStage.KNOCKOUT,
            round=first_round,
            match_order=i // 2
        )
        
        # Handle first participant (can be None)
        if i < len(seeded_participants):
            # Extract from the dictionary format
            participant_dict = seeded_participants[i]
            
            # Get the participant entity based on doubles/singles
            if is_doubles:
                participant1 = participant_dict.get('team')  # Can be None
                participant1_id = participant1.id if participant1 else None
                match.team1_id = participant1_id
            else:
                participant1 = participant_dict.get('player')  # Can be None
                participant1_id = participant1.id if participant1 else None
                match.player1_id = participant1_id
                
            # Always set the code if available
            code1 = participant_dict.get('code')
            match.player1_code = code1
        else:
            # No participant for this position
            if is_doubles:
                match.team1_id = None
            else:
                match.player1_id = None
            match.player1_code = f"R{first_round}-{i+1}"

        # Handle second participant (can be None)
        if (i + 1) < len(seeded_participants):
            # Extract from the dictionary format
            participant_dict = seeded_participants[i + 1]
            
            # Get the participant entity based on doubles/singles
            if is_doubles:
                participant2 = participant_dict.get('team')  # Can be None
                participant2_id = participant2.id if participant2 else None
                match.team2_id = participant2_id
            else:
                participant2 = participant_dict.get('player')  # Can be None
                participant2_id = participant2.id if participant2 else None
                match.player2_id = participant2_id
                
            # Always set the code if available
            code2 = participant_dict.get('code')
            match.player2_code = code2
        else:
            # No participant for this position
            if is_doubles:
                match.team2_id = None
            else:
                match.player2_id = None
            match.player2_code = f"R{first_round}-{i+2}"
            
        db.session.add(match)
        matches.append(match)
    
    db.session.flush()
    
    # Create subsequent rounds
    prev_round_matches = matches
    
    for r in range(first_round - 1, 0, -1):
        next_round_matches = []
        
        for i in range(0, len(prev_round_matches), 2):
            match = Match(
                category_id=category.id,
                stage=MatchStage.KNOCKOUT,
                round=r,
                match_order=i // 2
            )
            
            # Generate position codes for future matches based on round
            if r == 1:  # Finals
                match.player1_code = "SF1"  # Winner of first semi
                match.player2_code = "SF2"  # Winner of second semi
            elif r == 2:  # Semifinals
                if i == 0:
                    match.player1_code = "QF1"  # Winner of first quarter
                    match.player2_code = "QF2"  # Winner of second quarter
                else:
                    match.player1_code = "QF3"  # Winner of third quarter
                    match.player2_code = "QF4"  # Winner of fourth quarter
            elif r == 3:  # Quarterfinals
                match.player1_code = f"R16-{i*2+1}"  # Round of 16 winners
                match.player2_code = f"R16-{i*2+2}"
            elif r == 4:  # Round of 16
                match.player1_code = f"R32-{i*2+1}"
                match.player2_code = f"R32-{i*2+2}"
            elif r == 5:  # Round of 32
                match.player1_code = f"R64-{i*2+1}"
                match.player2_code = f"R64-{i*2+2}"
            else:  # Generic code for deeper rounds
                match.player1_code = f"R{r+1}-{i*2+1}"
                match.player2_code = f"R{r+1}-{i*2+2}"
            
            db.session.add(match)
            db.session.flush()
            
            # Link previous matches to this one
            if i < len(prev_round_matches):
                prev_round_matches[i].next_match_id = match.id
            
            if i + 1 < len(prev_round_matches):
                prev_round_matches[i + 1].next_match_id = match.id
            
            next_round_matches.append(match)
        
        prev_round_matches = next_round_matches
    
    # Create 3rd place match if needed
    if third_place_match and round_count >= 2:  # At least semifinal round exists
        semifinal_matches = Match.query.filter_by(
            category_id=category.id,
            stage=MatchStage.KNOCKOUT,
            round=2
        ).all()
        
        if len(semifinal_matches) == 2:
            match = Match(
                category_id=category.id,
                stage=MatchStage.PLAYOFF,
                round=1.5,  # Between final and semifinal
                match_order=0,
                player1_code="L-SF1",  # Loser of first semifinal
                player2_code="L-SF2"   # Loser of second semifinal
            )
            db.session.add(match)
    
    db.session.flush()

def update_match_seeds(category_id, seed_data):
    """
    Update registration seeds for a category based on manual seeding
    
    Args:
        category_id: The ID of the tournament category
        seed_data: Dictionary mapping registration_id -> seed value
    
    Returns:
        Boolean indicating success
    """
    try:
        for reg_id, seed_val in seed_data.items():
            try:
                reg_id = int(reg_id)
                seed_val = int(seed_val) if seed_val else None
                
                # Get the registration and verify it's for the right category
                reg = Registration.query.get(reg_id)
                if reg and reg.category_id == category_id:
                    reg.seed = seed_val
                    
            except (ValueError, TypeError) as e:
                current_app.logger.error(f"Invalid data in seed update: {reg_id} -> {seed_val}, Error: {str(e)}")
                # Continue processing other seeds even if one fails
        
        db.session.commit()
        return True
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating seeds: {str(e)}")
        return False
