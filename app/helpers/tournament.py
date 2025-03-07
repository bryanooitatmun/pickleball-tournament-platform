# Helper Functions


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
        else:
            match_info['team1_name'] = "TBD"
        
        if match.team2:
            match_info['team2_name'] = f"{match.team2.player1.full_name}/{match.team2.player2.full_name}"
        else:
            match_info['team2_name'] = "TBD"
        
        if hasattr(match, 'winner') and match.winner:
            match_info['winner_name'] = f"{match.winner.player1.full_name}/{match.winner.player2.full_name}"
    else:
        # Singles match
        if match.player1:
            match_info['player1_name'] = match.player1.full_name
        else:
            match_info['player1_name'] = "TBD"
        
        if match.player2:
            match_info['player2_name'] = match.player2.full_name
        else:
            match_info['player2_name'] = "TBD"
        
        if hasattr(match, 'winner') and match.winner:
            match_info['winner_name'] = match.winner.full_name
    
    # Add scores
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
    
    return match_info

def _generate_group_stage(category):
    """Generate group stage matches for a category"""
    if not category.group_count or not category.teams_per_group:
        return False
    
    # Get registrations
    registrations = Registration.query.filter_by(category_id=category.id).all()
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
    
    # Distribute teams to groups evenly
    # Sort by seed if available
    sorted_regs = sorted(registrations, key=lambda x: x.seed if x.seed else 999)
    
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
    
    # Distribute participants to groups (snake seeding)
    group_participants = [[] for _ in range(len(groups))]
    
    for i, participant in enumerate(participants):
        group_index = i % len(groups)
        # Reverse direction on even passes
        if (i // len(groups)) % 2 == 1:
            group_index = len(groups) - 1 - group_index
        
        group_participants[group_index].append(participant)
    
    # Create group standings and matches
    for i, group in enumerate(groups):
        # Create standings
        for participant in group_participants[i]:
            standing = GroupStanding(group_id=group.id)
            
            if is_doubles:
                standing.team_id = participant.id
            else:
                standing.player_id = participant.id
            
            db.session.add(standing)
        
        # Create round-robin matches
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
                
                if is_doubles:
                    match.team1_id = team1.id
                    match.team2_id = team2.id
                else:
                    match.player1_id = team1.id
                    match.player2_id = team2.id
                
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
    
    for group in groups:
        # Get standings sorted by position
        standings = GroupStanding.query.filter_by(group_id=group.id)\
            .order_by(GroupStanding.position).limit(category.teams_advancing_per_group).all()
        
        for standing in standings:
            if is_doubles:
                advancing_participants.append({
                    'team': standing.team,
                    'group': group.name,
                    'position': standing.position
                })
            else:
                advancing_participants.append({
                    'player': standing.player,
                    'group': group.name,
                    'position': standing.position
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
    
    # Generate knockout matches
    _create_knockout_matches(category, seeded_participants, is_doubles)
    
    db.session.commit()
    return True

def _generate_single_elimination(category):
    """Generate single elimination bracket from registrations"""
    # Get registrations
    registrations = Registration.query.filter_by(category_id=category.id).all()
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
    
    # Sort by seed if available (None seeds at the end)
    sorted_participants = sorted(
        participants,
        key=lambda p: p['seed'] if p['seed'] else 999
    )
    
    # Extract just the player/team from each entry
    seeded_participants = []
    for p in sorted_participants:
        if is_doubles:
            seeded_participants.append(p['team'])
        else:
            seeded_participants.append(p['player'])
    
    # Determine bracket size (next power of 2)
    bracket_size = 1
    while bracket_size < len(seeded_participants):
        bracket_size *= 2
    
    # Add byes to fill bracket
    while len(seeded_participants) < bracket_size:
        seeded_participants.append(None)
    
    # Generate knockout matches
    _create_knockout_matches(category, seeded_participants, is_doubles)
    
    db.session.commit()
    return True

def _create_knockout_matches(category, seeded_participants, is_doubles):
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
        
        team1 = seeded_participants[i]
        team2 = seeded_participants[i + 1] if i + 1 < n else None
        
        if is_doubles:
            match.team1_id = team1.id if team1 else None
            match.team2_id = team2.id if team2 else None
        else:
            match.player1_id = team1.id if team1 else None
            match.player2_id = team2.id if team2 else None
        
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
    if round_count >= 2:  # At least semifinal round exists
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
                match_order=0
            )
            db.session.add(match)
    
    db.session.flush()