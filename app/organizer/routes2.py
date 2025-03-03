# Continuation of organizer routes

@bp.route('/tournament/<int:id>/category/<int:category_id>/match/<int:match_id>/complete', methods=['POST'])
@login_required
@organizer_required
def complete_match(id, category_id, match_id):
    tournament = Tournament.query.get_or_404(id)
    match = Match.query.get_or_404(match_id)
    
    # Check if this tournament belongs to the current user
    if tournament.organizer_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to manage this tournament.', 'danger')
        return redirect(url_for('organizer.dashboard'))
    
    form = CompleteMatchForm()
    
    if form.validate_on_submit():
        match_id = form.match_id.data
        winner_id = form.winner_id.data
        completed = form.completed.data
        
        match = Match.query.get_or_404(match_id)
        
        # Set winner and loser
        match.winner_id = winner_id
        if winner_id == match.player1_id:
            match.loser_id = match.player2_id
        else:
            match.loser_id = match.player1_id
        
        match.completed = completed
        
        # If match is completed and has a next match, advance the winner
        if completed and match.next_match_id:
            next_match = Match.query.get(match.next_match_id)
            if next_match:
                # Determine if winner should be player1 or player2 in next match
                if match.match_order % 2 == 0:
                    next_match.player1_id = winner_id
                    if match.player1_partner_id and match.player1_id == winner_id:
                        next_match.player1_partner_id = match.player1_partner_id
                    elif match.player2_partner_id and match.player2_id == winner_id:
                        next_match.player1_partner_id = match.player2_partner_id
                else:
                    next_match.player2_id = winner_id
                    if match.player1_partner_id and match.player1_id == winner_id:
                        next_match.player2_partner_id = match.player1_partner_id
                    elif match.player2_partner_id and match.player2_id == winner_id:
                        next_match.player2_partner_id = match.player2_partner_id
        
        db.session.commit()
        
        flash('Match completed successfully!', 'success')
        return redirect(url_for('organizer.manage_category', id=id, category_id=category_id))
    
    return redirect(url_for('organizer.manage_category', id=id, category_id=category_id))

@bp.route('/tournament/<int:id>/category/<int:category_id>/finalize', methods=['POST'])
@login_required
@organizer_required
def finalize_category(id, category_id):
    tournament = Tournament.query.get_or_404(id)
    category = TournamentCategory.query.get_or_404(category_id)
    
    # Check if this tournament belongs to the current user
    if tournament.organizer_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to manage this tournament.', 'danger')
        return redirect(url_for('organizer.dashboard'))
    
    # Check if all matches are completed
    incomplete_matches = Match.query.filter_by(category_id=category_id, completed=False).count()
    if incomplete_matches > 0:
        flash(f'Cannot finalize category with {incomplete_matches} incomplete matches.', 'warning')
        return redirect(url_for('organizer.manage_category', id=id, category_id=category_id))
    
    # Get the final match (round 1)
    final_match = Match.query.filter_by(category_id=category_id, round=1).first()
    
    if not final_match or not final_match.winner_id:
        flash('Cannot finalize category without a winner.', 'warning')
        return redirect(url_for('organizer.manage_category', id=id, category_id=category_id))
    
    # Award points to players based on their placement
    winner_profile = PlayerProfile.query.get(final_match.winner_id)
    runner_up_profile = PlayerProfile.query.get(final_match.loser_id)
    
    # Get point values from config
    points_distribution = current_app.config['POINTS_DISTRIBUTION']
    total_points = category.points_awarded
    
    # Award points based on category type
    if category.category_type == CategoryType.MENS_SINGLES:
        if winner_profile:
            winner_profile.mens_singles_points += int(total_points * points_distribution[1] / 100)
        if runner_up_profile:
            runner_up_profile.mens_singles_points += int(total_points * points_distribution[2] / 100)
    
    elif category.category_type == CategoryType.WOMENS_SINGLES:
        if winner_profile:
            winner_profile.womens_singles_points += int(total_points * points_distribution[1] / 100)
        if runner_up_profile:
            runner_up_profile.womens_singles_points += int(total_points * points_distribution[2] / 100)
    
    elif category.category_type == CategoryType.MENS_DOUBLES:
        if winner_profile:
            winner_profile.mens_doubles_points += int(total_points * points_distribution[1] / 100)
        if runner_up_profile:
            runner_up_profile.mens_doubles_points += int(total_points * points_distribution[2] / 100)
        
        # Award points to partners as well
        if final_match.player1_partner_id and final_match.player1_id == final_match.winner_id:
            partner_profile = PlayerProfile.query.get(final_match.player1_partner_id)
            if partner_profile:
                partner_profile.mens_doubles_points += int(total_points * points_distribution[1] / 100)
        
        if final_match.player2_partner_id and final_match.player2_id == final_match.winner_id:
            partner_profile = PlayerProfile.query.get(final_match.player2_partner_id)
            if partner_profile:
                partner_profile.mens_doubles_points += int(total_points * points_distribution[1] / 100)
        
        if final_match.player1_partner_id and final_match.player1_id == final_match.loser_id:
            partner_profile = PlayerProfile.query.get(final_match.player1_partner_id)
            if partner_profile:
                partner_profile.mens_doubles_points += int(total_points * points_distribution[2] / 100)
        
        if final_match.player2_partner_id and final_match.player2_id == final_match.loser_id:
            partner_profile = PlayerProfile.query.get(final_match.player2_partner_id)
            if partner_profile:
                partner_profile.mens_doubles_points += int(total_points * points_distribution[2] / 100)
    
    elif category.category_type == CategoryType.WOMENS_DOUBLES:
        if winner_profile:
            winner_profile.womens_doubles_points += int(total_points * points_distribution[1] / 100)
        if runner_up_profile:
            runner_up_profile.womens_doubles_points += int(total_points * points_distribution[2] / 100)
        
        # Award points to partners as well
        if final_match.player1_partner_id and final_match.player1_id == final_match.winner_id:
            partner_profile = PlayerProfile.query.get(final_match.player1_partner_id)
            if partner_profile:
                partner_profile.womens_doubles_points += int(total_points * points_distribution[1] / 100)
        
        if final_match.player2_partner_id and final_match.player2_id == final_match.winner_id:
            partner_profile = PlayerProfile.query.get(final_match.player2_partner_id)
            if partner_profile:
                partner_profile.womens_doubles_points += int(total_points * points_distribution[1] / 100)
        
        if final_match.player1_partner_id and final_match.player1_id == final_match.loser_id:
            partner_profile = PlayerProfile.query.get(final_match.player1_partner_id)
            if partner_profile:
                partner_profile.womens_doubles_points += int(total_points * points_distribution[2] / 100)
        
        if final_match.player2_partner_id and final_match.player2_id == final_match.loser_id:
            partner_profile = PlayerProfile.query.get(final_match.player2_partner_id)
            if partner_profile:
                partner_profile.womens_doubles_points += int(total_points * points_distribution[2] / 100)
    
    elif category.category_type == CategoryType.MIXED_DOUBLES:
        if winner_profile:
            winner_profile.mixed_doubles_points += int(total_points * points_distribution[1] / 100)
        if runner_up_profile:
            runner_up_profile.mixed_doubles_points += int(total_points * points_distribution[2] / 100)
        
        # Award points to partners as well
        if final_match.player1_partner_id and final_match.player1_id == final_match.winner_id:
            partner_profile = PlayerProfile.query.get(final_match.player1_partner_id)
            if partner_profile:
                partner_profile.mixed_doubles_points += int(total_points * points_distribution[1] / 100)
        
        if final_match.player2_partner_id and final_match.player2_id == final_match.winner_id:
            partner_profile = PlayerProfile.query.get(final_match.player2_partner_id)
            if partner_profile:
                partner_profile.mixed_doubles_points += int(total_points * points_distribution[1] / 100)
        
        if final_match.player1_partner_id and final_match.player1_id == final_match.loser_id:
            partner_profile = PlayerProfile.query.get(final_match.player1_partner_id)
            if partner_profile:
                partner_profile.mixed_doubles_points += int(total_points * points_distribution[2] / 100)
        
        if final_match.player2_partner_id and final_match.player2_id == final_match.loser_id:
            partner_profile = PlayerProfile.query.get(final_match.player2_partner_id)
            if partner_profile:
                partner_profile.mixed_doubles_points += int(total_points * points_distribution[2] / 100)
    
    # Award points to semifinalists (3rd and 4th place)
    semifinal_matches = Match.query.filter_by(category_id=category_id, round=2).all()
    
    for semifinal in semifinal_matches:
        if semifinal.loser_id:
            semifinalist_profile = PlayerProfile.query.get(semifinal.loser_id)
            if semifinalist_profile:
                # Award points based on category
                if category.category_type == CategoryType.MENS_SINGLES:
                    semifinalist_profile.mens_singles_points += int(total_points * points_distribution[3] / 100)
                elif category.category_type == CategoryType.WOMENS_SINGLES:
                    semifinalist_profile.womens_singles_points += int(total_points * points_distribution[3] / 100)
                elif category.category_type == CategoryType.MENS_DOUBLES:
                    semifinalist_profile.mens_doubles_points += int(total_points * points_distribution[3] / 100)
                    
                    # Award points to partner
                    if semifinal.player1_partner_id and semifinal.player1_id == semifinal.loser_id:
                        partner_profile = PlayerProfile.query.get(semifinal.player1_partner_id)
                        if partner_profile:
                            partner_profile.mens_doubles_points += int(total_points * points_distribution[3] / 100)
                    
                    if semifinal.player2_partner_id and semifinal.player2_id == semifinal.loser_id:
                        partner_profile = PlayerProfile.query.get(semifinal.player2_partner_id)
                        if partner_profile:
                            partner_profile.mens_doubles_points += int(total_points * points_distribution[3] / 100)
                    
                elif category.category_type == CategoryType.WOMENS_DOUBLES:
                    semifinalist_profile.womens_doubles_points += int(total_points * points_distribution[3] / 100)
                    
                    # Award points to partner
                    if semifinal.player1_partner_id and semifinal.player1_id == semifinal.loser_id:
                        partner_profile = PlayerProfile.query.get(semifinal.player1_partner_id)
                        if partner_profile:
                            partner_profile.womens_doubles_points += int(total_points * points_distribution[3] / 100)
                    
                    if semifinal.player2_partner_id and semifinal.player2_id == semifinal.loser_id:
                        partner_profile = PlayerProfile.query.get(semifinal.player2_partner_id)
                        if partner_profile:
                            partner_profile.womens_doubles_points += int(total_points * points_distribution[3] / 100)
                    
                elif category.category_type == CategoryType.MIXED_DOUBLES:
                    semifinalist_profile.mixed_doubles_points += int(total_points * points_distribution[3] / 100)
                    
                    # Award points to partner
                    if semifinal.player1_partner_id and semifinal.player1_id == semifinal.loser_id:
                        partner_profile = PlayerProfile.query.get(semifinal.player1_partner_id)
                        if partner_profile:
                            partner_profile.mixed_doubles_points += int(total_points * points_distribution[3] / 100)
                    
                    if semifinal.player2_partner_id and semifinal.player2_id == semifinal.loser_id:
                        partner_profile = PlayerProfile.query.get(semifinal.player2_partner_id)
                        if partner_profile:
                            partner_profile.mixed_doubles_points += int(total_points * points_distribution[3] / 100)
    
    db.session.commit()
    
    flash('Category finalized and points awarded to players!', 'success')
    return redirect(url_for('organizer.manage_category', id=id, category_id=category_id))

@bp.route('/tournament/<int:id>/finalize', methods=['POST'])
@login_required
@organizer_required
def finalize_tournament(id):
    tournament = Tournament.query.get_or_404(id)
    
    # Check if this tournament belongs to the current user
    if tournament.organizer_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to manage this tournament.', 'danger')
        return redirect(url_for('organizer.dashboard'))
    
    # Check if all categories have been finalized
    all_finalized = True
    categories = tournament.categories.all()
    
    for category in categories:
        # Check if all matches are completed
        incomplete_matches = Match.query.filter_by(category_id=category.id, completed=False).count()
        if incomplete_matches > 0:
            all_finalized = False
            break
    
    if not all_finalized:
        flash('Cannot finalize tournament until all categories have been finalized.', 'warning')
        return redirect(url_for('organizer.tournament_detail', id=id))
    
    # Mark tournament as completed
    tournament.status = TournamentStatus.COMPLETED
    db.session.commit()
    
    flash('Tournament finalized successfully!', 'success')
    return redirect(url_for('organizer.tournament_detail', id=id))

@bp.route('/tournament/<int:id>/export_results')
@login_required
@organizer_required
def export_results(id):
    tournament = Tournament.query.get_or_404(id)
    
    # Check if this tournament belongs to the current user
    if tournament.organizer_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to manage this tournament.', 'danger')
        return redirect(url_for('organizer.dashboard'))
    
    # Prepare data for export
    result_data = {
        'tournament': {
            'id': tournament.id,
            'name': tournament.name,
            'location': tournament.location,
            'start_date': tournament.start_date.strftime('%Y-%m-%d'),
            'end_date': tournament.end_date.strftime('%Y-%m-%d'),
            'tier': tournament.tier.value,
            'format': tournament.format.value,
            'status': tournament.status.value,
            'prize_pool': tournament.prize_pool
        },
        'categories': []
    }
    
    categories = tournament.categories.all()
    for category in categories:
        category_data = {
            'id': category.id,
            'type': category.category_type.value,
            'points_awarded': category.points_awarded,
            'winners': [],
            'matches': []
        }
        
        # Get final match to determine winners
        final_match = Match.query.filter_by(category_id=category.id, round=1).first()
        if final_match and final_match.winner_id:
            winner = PlayerProfile.query.get(final_match.winner_id)
            runner_up = PlayerProfile.query.get(final_match.loser_id)
            
            if winner:
                category_data['winners'].append({
                    'place': 1,
                    'player_id': winner.id,
                    'player_name': winner.full_name,
                    'country': winner.country
                })
            
            if runner_up:
                category_data['winners'].append({
                    'place': 2,
                    'player_id': runner_up.id,
                    'player_name': runner_up.full_name,
                    'country': runner_up.country
                })
        
        # Get completed matches
        matches = Match.query.filter_by(category_id=category.id, completed=True).all()
        for match in matches:
            match_data = {
                'id': match.id,
                'round': match.round,
                'player1_id': match.player1_id,
                'player2_id': match.player2_id,
                'winner_id': match.winner_id,
                'scores': []
            }
            
            # Add player names
            if match.player1_id:
                player1 = PlayerProfile.query.get(match.player1_id)
                if player1:
                    match_data['player1_name'] = player1.full_name
            
            if match.player2_id:
                player2 = PlayerProfile.query.get(match.player2_id)
                if player2:
                    match_data['player2_name'] = player2.full_name
            
            # Add scores
            scores = MatchScore.query.filter_by(match_id=match.id).order_by(MatchScore.set_number).all()
            for score in scores:
                match_data['scores'].append({
                    'set': score.set_number,
                    'player1_score': score.player1_score,
                    'player2_score': score.player2_score
                })
            
            category_data['matches'].append(match_data)
        
        result_data['categories'].append(category_data)
    
    # Return JSON response
    return jsonify(result_data)
