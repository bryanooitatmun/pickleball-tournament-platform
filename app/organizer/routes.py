from flask import render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
import os
import math
import random
from datetime import datetime, timedelta

from app import db
from app.organizer import bp
from app.organizer.forms import (TournamentForm, CategoryForm, SeedingForm, 
                                MatchForm, ScoreForm, BracketGenerationForm,
                                CompleteMatchForm)
from app.models import (Tournament, TournamentCategory, Match, MatchScore, 
                       Registration, PlayerProfile, User, TournamentStatus,
                       TournamentTier, TournamentFormat, CategoryType)

from app.decorators import organizer_required

def save_picture(picture, subfolder='tournament_pics'):
    # Generate a secure filename
    filename = secure_filename(picture.filename)
    
    # Generate a unique filename with timestamp
    unique_filename = f"{subfolder}_{int(datetime.utcnow().timestamp())}_{filename}"
    
    # Create full path
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder, unique_filename)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Save the file
    picture.save(file_path)
    
    # Return the relative path for the database
    return os.path.join('uploads', subfolder, unique_filename)

@bp.route('/dashboard')
@login_required
@organizer_required
def dashboard():
    # Get tournaments organized by this user
    tournaments = Tournament.query.filter_by(organizer_id=current_user.id).order_by(Tournament.start_date.desc()).all()
    
    # Split tournaments by status
    upcoming_tournaments = [t for t in tournaments if t.status == TournamentStatus.UPCOMING]
    ongoing_tournaments = [t for t in tournaments if t.status == TournamentStatus.ONGOING]
    completed_tournaments = [t for t in tournaments if t.status == TournamentStatus.COMPLETED]
    
    return render_template('organizer/dashboard.html',
                           title='Organizer Dashboard',
                           upcoming_tournaments=upcoming_tournaments,
                           ongoing_tournaments=ongoing_tournaments,
                           completed_tournaments=completed_tournaments)

@bp.route('/tournament/create', methods=['GET', 'POST'])
@login_required
@organizer_required
def create_tournament():
    form = TournamentForm()
    
    if form.validate_on_submit():
        tournament = Tournament(
            name=form.name.data,
            organizer_id=current_user.id,
            location=form.location.data,
            description=form.description.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            registration_deadline=form.registration_deadline.data,
            tier=TournamentTier[form.tier.data],
            format=TournamentFormat[form.format.data],
            status=TournamentStatus[form.status.data],
            prize_pool=form.prize_pool.data
        )
        
        # Handle logo upload
        if form.logo.data:
            tournament.logo = save_picture(form.logo.data, 'tournament_logos')
        
        # Handle banner upload
        if form.banner.data:
            tournament.banner = save_picture(form.banner.data, 'tournament_banners')
        
        db.session.add(tournament)
        db.session.commit()
        
        flash('Tournament created successfully!', 'success')
        return redirect(url_for('organizer.tournament_detail', id=tournament.id))
    
    return render_template('organizer/create_tournament.html',
                           title='Create Tournament',
                           form=form)

@bp.route('/tournament/<int:id>')
@login_required
@organizer_required
def tournament_detail(id):
    tournament = Tournament.query.get_or_404(id)
    
    # Check if this tournament belongs to the current user
    if tournament.organizer_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to view this tournament.', 'danger')
        return redirect(url_for('organizer.dashboard'))
    
    # Get categories for this tournament
    categories = tournament.categories.all()
    
    # Get registrations by category
    registrations = {}
    for category in categories:
        registrations[category.id] = Registration.query.filter_by(category_id=category.id).all()
    
    return render_template('organizer/tournament_detail.html',
                           title=f'Manage: {tournament.name}',
                           tournament=tournament,
                           categories=categories,
                           registrations=registrations)

@bp.route('/tournament/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@organizer_required
def edit_tournament(id):
    tournament = Tournament.query.get_or_404(id)
    
    # Check if this tournament belongs to the current user
    if tournament.organizer_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to edit this tournament.', 'danger')
        return redirect(url_for('organizer.dashboard'))
    
    form = TournamentForm(obj=tournament)
    
    if form.validate_on_submit():
        tournament.name = form.name.data
        tournament.location = form.location.data
        tournament.description = form.description.data
        tournament.start_date = form.start_date.data
        tournament.end_date = form.end_date.data
        tournament.registration_deadline = form.registration_deadline.data
        tournament.tier = TournamentTier[form.tier.data]
        tournament.format = TournamentFormat[form.format.data]
        tournament.status = TournamentStatus[form.status.data]
        tournament.prize_pool = form.prize_pool.data
        
        # Handle logo upload
        if form.logo.data:
            tournament.logo = save_picture(form.logo.data, 'tournament_logos')
        
        # Handle banner upload
        if form.banner.data:
            tournament.banner = save_picture(form.banner.data, 'tournament_banners')
        
        db.session.commit()
        
        flash('Tournament updated successfully!', 'success')
        return redirect(url_for('organizer.tournament_detail', id=tournament.id))
    
    # Pre-populate form with enum names
    form.tier.data = tournament.tier.name
    form.format.data = tournament.format.name
    form.status.data = tournament.status.name
    
    return render_template('organizer/edit_tournament.html',
                           title=f'Edit: {tournament.name}',
                           form=form,
                           tournament=tournament)

@bp.route('/tournament/<int:id>/add_category', methods=['GET', 'POST'])
@login_required
@organizer_required
def add_category(id):
    tournament = Tournament.query.get_or_404(id)
    
    # Check if this tournament belongs to the current user
    if tournament.organizer_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to edit this tournament.', 'danger')
        return redirect(url_for('organizer.dashboard'))
    
    form = CategoryForm()
    
    if form.validate_on_submit():
        # Check if category already exists
        existing_category = TournamentCategory.query.filter_by(
            tournament_id=id,
            category_type=CategoryType[form.category_type.data]
        ).first()
        
        if existing_category:
            flash(f'This tournament already has a {form.category_type.data} category.', 'warning')
        else:
            category = TournamentCategory(
                tournament_id=id,
                category_type=CategoryType[form.category_type.data],
                max_participants=form.max_participants.data,
                points_awarded=form.points_awarded.data
            )
            
            db.session.add(category)
            db.session.commit()
            
            flash('Category added successfully!', 'success')
        
        return redirect(url_for('organizer.tournament_detail', id=id))
    
    return render_template('organizer/add_category.html',
                           title=f'Add Category to {tournament.name}',
                           form=form,
                           tournament=tournament)

@bp.route('/tournament/<int:id>/category/<int:category_id>/manage')
@login_required
@organizer_required
def manage_category(id, category_id):
    tournament = Tournament.query.get_or_404(id)
    category = TournamentCategory.query.get_or_404(category_id)
    
    # Check if this tournament belongs to the current user
    if tournament.organizer_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to manage this tournament.', 'danger')
        return redirect(url_for('organizer.dashboard'))
    
    # Check if category belongs to this tournament
    if category.tournament_id != id:
        flash('Category not found in this tournament.', 'danger')
        return redirect(url_for('organizer.tournament_detail', id=id))
    
    # Get registrations for this category
    registrations = Registration.query.filter_by(category_id=category_id).all()
    
    # Get matches for this category
    matches = Match.query.filter_by(category_id=category_id).order_by(Match.round.desc(), Match.match_order).all()
    
    return render_template('organizer/manage_category.html',
                           title=f'Manage {category.category_type.value}',
                           tournament=tournament,
                           category=category,
                           registrations=registrations,
                           matches=matches)

@bp.route('/tournament/<int:id>/category/<int:category_id>/registrations')
@login_required
@organizer_required
def manage_registrations(id, category_id):
    tournament = Tournament.query.get_or_404(id)
    category = TournamentCategory.query.get_or_404(category_id)
    
    # Check if this tournament belongs to the current user
    if tournament.organizer_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to manage this tournament.', 'danger')
        return redirect(url_for('organizer.dashboard'))
    
    # Check if category belongs to this tournament
    if category.tournament_id != id:
        flash('Category not found in this tournament.', 'danger')
        return redirect(url_for('organizer.tournament_detail', id=id))
    
    # Get registrations for this category
    registrations = Registration.query.filter_by(category_id=category_id).all()
    
    return render_template('organizer/manage_registrations.html',
                           title=f'Manage Registrations for {category.category_type.value}',
                           tournament=tournament,
                           category=category,
                           registrations=registrations)

@bp.route('/tournament/<int:id>/category/<int:category_id>/approve_registration/<int:registration_id>', methods=['POST'])
@login_required
@organizer_required
def approve_registration(id, category_id, registration_id):
    tournament = Tournament.query.get_or_404(id)
    
    # Check if this tournament belongs to the current user
    if tournament.organizer_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to manage this tournament.', 'danger')
        return redirect(url_for('organizer.dashboard'))
    
    registration = Registration.query.get_or_404(registration_id)
    
    # Check if registration belongs to this category
    if registration.category_id != category_id:
        flash('Registration not found in this category.', 'danger')
        return redirect(url_for('organizer.manage_registrations', id=id, category_id=category_id))
    
    # Approve registration
    registration.is_approved = True
    db.session.commit()
    
    flash('Registration approved successfully!', 'success')
    return redirect(url_for('organizer.manage_registrations', id=id, category_id=category_id))

@bp.route('/tournament/<int:id>/category/<int:category_id>/reject_registration/<int:registration_id>', methods=['POST'])
@login_required
@organizer_required
def reject_registration(id, category_id, registration_id):
    tournament = Tournament.query.get_or_404(id)
    
    # Check if this tournament belongs to the current user
    if tournament.organizer_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to manage this tournament.', 'danger')
        return redirect(url_for('organizer.dashboard'))
    
    registration = Registration.query.get_or_404(registration_id)
    
    # Check if registration belongs to this category
    if registration.category_id != category_id:
        flash('Registration not found in this category.', 'danger')
        return redirect(url_for('organizer.manage_registrations', id=id, category_id=category_id))
    
    # Delete registration
    db.session.delete(registration)
    db.session.commit()
    
    flash('Registration rejected and removed.', 'success')
    return redirect(url_for('organizer.manage_registrations', id=id, category_id=category_id))

@bp.route('/tournament/<int:id>/category/<int:category_id>/update_seed/<int:registration_id>', methods=['POST'])
@login_required
@organizer_required
def update_seed(id, category_id, registration_id):
    tournament = Tournament.query.get_or_404(id)
    
    # Check if this tournament belongs to the current user
    if tournament.organizer_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to manage this tournament.', 'danger')
        return redirect(url_for('organizer.dashboard'))
    
    registration = Registration.query.get_or_404(registration_id)
    
    # Check if registration belongs to this category
    if registration.category_id != category_id:
        flash('Registration not found in this category.', 'danger')
        return redirect(url_for('organizer.manage_registrations', id=id, category_id=category_id))
    
    form = SeedingForm()
    
    if form.validate_on_submit():
        registration.seed = form.seed.data
        db.session.commit()
        
        flash('Seed updated successfully!', 'success')
    
    return redirect(url_for('organizer.manage_registrations', id=id, category_id=category_id))

@bp.route('/tournament/<int:id>/category/<int:category_id>/generate_bracket', methods=['GET', 'POST'])
@login_required
@organizer_required
def generate_bracket(id, category_id):
    tournament = Tournament.query.get_or_404(id)
    category = TournamentCategory.query.get_or_404(category_id)
    
    # Check if this tournament belongs to the current user
    if tournament.organizer_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to manage this tournament.', 'danger')
        return redirect(url_for('organizer.dashboard'))
    
    # Check if category belongs to this tournament
    if category.tournament_id != id:
        flash('Category not found in this tournament.', 'danger')
        return redirect(url_for('organizer.tournament_detail', id=id))
    
    form = BracketGenerationForm()
    form.category_id.data = category_id
    
    if form.validate_on_submit():
        # Get approved registrations
        registrations = Registration.query.filter_by(
            category_id=category_id,
            is_approved=True
        ).all()
        
        # Check if there are enough participants
        if len(registrations) < 2:
            flash('Need at least 2 approved participants to generate a bracket.', 'warning')
            return redirect(url_for('organizer.manage_category', id=id, category_id=category_id))
        
        # Delete existing matches for this category
        Match.query.filter_by(category_id=category_id).delete()
        db.session.commit()
        
        # Generate bracket based on tournament format
        if tournament.format == TournamentFormat.SINGLE_ELIMINATION:
            generate_single_elimination_bracket(category, registrations, form.use_seeding.data, form.third_place_match.data)
        elif tournament.format == TournamentFormat.DOUBLE_ELIMINATION:
            # This would be more complex to implement
            flash('Double elimination bracket generation not yet implemented.', 'warning')
        elif tournament.format == TournamentFormat.ROUND_ROBIN:
            generate_round_robin(category, registrations)
        elif tournament.format == TournamentFormat.GROUP_KNOCKOUT:
            # This would require group stage setup first
            flash('Group stage + knockout format not yet implemented.', 'warning')
        
        flash('Bracket generated successfully!', 'success')
        return redirect(url_for('organizer.manage_category', id=id, category_id=category_id))
    
    return render_template('organizer/generate_bracket.html',
                           title=f'Generate Bracket for {category.category_type.value}',
                           tournament=tournament,
                           category=category,
                           form=form)

def generate_single_elimination_bracket(category, registrations, use_seeding=True, third_place_match=False):
    # Get the number of participants and calculate bracket size
    num_participants = len(registrations)
    bracket_size = 1
    while bracket_size < num_participants:
        bracket_size *= 2
    
    # Initialize players list - will contain player IDs or None for byes
    players = []
    
    if use_seeding:
        # Sort registrations by seed (if available)
        registrations.sort(key=lambda r: r.seed if r.seed else 999)
        
        # Create a properly seeded bracket (this is a simplified version)
        # In a real implementation, you'd use a proper seeding algorithm
        for reg in registrations:
            players.append(reg.player_id)
        
        # Add byes for empty spots
        players.extend([None] * (bracket_size - len(players)))
    else:
        # Randomize the order
        player_ids = [reg.player_id for reg in registrations]
        random.shuffle(player_ids)
        players = player_ids
        
        # Add byes for empty spots
        players.extend([None] * (bracket_size - len(players)))
    
    # Calculate number of rounds
    num_rounds = int(math.log2(bracket_size))
    
    # Create matches for each round
    matches = []
    match_count_by_round = {}
    
    # Create first round matches
    for i in range(0, bracket_size, 2):
        player1_id = players[i]
        player2_id = players[i + 1]
        
        # If one player has a bye, they advance automatically
        if player1_id is None and player2_id is not None:
            # Player 2 advances
            next_round_match_order = i // 4
            next_round_player_position = (i // 2) % 2  # 0 for player1, 1 for player2
            
            # Create new match
            match = Match(
                category_id=category.id,
                round=num_rounds,
                match_order=i // 2,
                player1_id=None,
                player2_id=player2_id
            )
            db.session.add(match)
            matches.append(match)
            
        elif player1_id is not None and player2_id is None:
            # Player 1 advances
            next_round_match_order = i // 4
            next_round_player_position = (i // 2) % 2  # 0 for player1, 1 for player2
            
            # Create new match
            match = Match(
                category_id=category.id,
                round=num_rounds,
                match_order=i // 2,
                player1_id=player1_id,
                player2_id=None
            )
            db.session.add(match)
            matches.append(match)
            
        elif player1_id is not None and player2_id is not None:
            # Regular match
            match = Match(
                category_id=category.id,
                round=num_rounds,
                match_order=i // 2,
                player1_id=player1_id,
                player2_id=player2_id
            )
            db.session.add(match)
            matches.append(match)
        
        # Skip if both players are None (empty match)
    
    # Create matches for subsequent rounds
    for round_num in range(num_rounds - 1, 0, -1):
        matches_in_round = 2 ** (round_num - 1)
        for i in range(matches_in_round):
            match = Match(
                category_id=category.id,
                round=round_num,
                match_order=i
            )
            db.session.add(match)
            matches.append(match)
    
    # Create third place match if requested
    if third_place_match:
        match = Match(
            category_id=category.id,
            round=1.5,  # Use a special round number for third place match
            match_order=0
        )
        db.session.add(match)
        matches.append(match)
    
    db.session.commit()
    
    # Link matches to set up advancement path
    for match in matches:
        if match.round > 1:
            # Find the next match in the bracket
            next_round = match.round - 1
            next_match_order = match.match_order // 2
            
            next_match = next((m for m in matches if m.round == next_round and m.match_order == next_match_order), None)
            
            if next_match:
                match.next_match_id = next_match.id
    
    db.session.commit()

def generate_round_robin(category, registrations):
    # Get all player IDs
    player_ids = [reg.player_id for reg in registrations]
    num_players = len(player_ids)
    
    # Make sure we have an even number of players
    if num_players % 2 == 1:
        player_ids.append(None)  # Add a "bye" player
        num_players += 1
    
    # Calculate number of rounds and matches per round
    num_rounds = num_players - 1
    matches_per_round = num_players // 2
    
    # Create schedule using circle method
    # Keep one player fixed and rotate the rest
    fixed_player = player_ids[0]
    rotating_players = player_ids[1:]
    
    round_num = 1
    for _ in range(num_rounds):
        # Create matches for this round
        for i in range(matches_per_round):
            player1_id = None
            player2_id = None
            
            if i == 0:
                player1_id = fixed_player
                player2_id = rotating_players[0]
            else:
                player1_id = rotating_players[i]
                player2_id = rotating_players[num_players - 2 - i]
            
            # Skip matches involving the "bye" player
            if player1_id is not None and player2_id is not None:
                match = Match(
                    category_id=category.id,
                    round=round_num,
                    match_order=i,
                    player1_id=player1_id,
                    player2_id=player2_id
                )
                db.session.add(match)
        
        # Rotate players for next round
        rotating_players.insert(0, rotating_players.pop())
        round_num += 1
    
    db.session.commit()

@bp.route('/tournament/<int:id>/category/<int:category_id>/match/<int:match_id>/edit', methods=['GET', 'POST'])
@login_required
@organizer_required
def edit_match(id, category_id, match_id):
    tournament = Tournament.query.get_or_404(id)
    category = TournamentCategory.query.get_or_404(category_id)
    match = Match.query.get_or_404(match_id)
    
    # Check if this tournament belongs to the current user
    if tournament.organizer_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to manage this tournament.', 'danger')
        return redirect(url_for('organizer.dashboard'))
    
    # Check if match belongs to this category
    if match.category_id != category_id:
        flash('Match not found in this category.', 'danger')
        return redirect(url_for('organizer.manage_category', id=id, category_id=category_id))
    
    form = MatchForm(obj=match)
    
    # Get all registered players for this category
    registrations = Registration.query.filter_by(category_id=category_id, is_approved=True).all()
    players = [(0, 'TBD')]
    for reg in registrations:
        player = PlayerProfile.query.get(reg.player_id)
        if player:
            players.append((player.id, player.full_name))
    
    form.player1_id.choices = players
    form.player2_id.choices = players
    form.player1_partner_id.choices = players
    form.player2_partner_id.choices = players
    
    if form.validate_on_submit():
        match.court = form.court.data
        
        # Combine date and time
        if form.scheduled_time.data and form.scheduled_time_hour.data:
            match.scheduled_time = datetime.combine(
                form.scheduled_time.data,
                form.scheduled_time_hour.data
            )
        
        match.player1_id = form.player1_id.data if form.player1_id.data != 0 else None
        match.player2_id = form.player2_id.data if form.player2_id.data != 0 else None
        
        # Handle doubles partners
        if category.category_type in [CategoryType.MENS_DOUBLES, CategoryType.WOMENS_DOUBLES, CategoryType.MIXED_DOUBLES]:
            match.player1_partner_id = form.player1_partner_id.data if form.player1_partner_id.data != 0 else None
            match.player2_partner_id = form.player2_partner_id.data if form.player2_partner_id.data != 0 else None
        
        db.session.commit()
        
        flash('Match updated successfully!', 'success')
        return redirect(url_for('organizer.manage_category', id=id, category_id=category_id))
    
    # Pre-populate form
    if match.player1_id:
        form.player1_id.data = match.player1_id
    if match.player2_id:
        form.player2_id.data = match.player2_id
    if match.player1_partner_id:
        form.player1_partner_id.data = match.player1_partner_id
    if match.player2_partner_id:
        form.player2_partner_id.data = match.player2_partner_id
    
    if match.scheduled_time:
        form.scheduled_time.data = match.scheduled_time.date()
        form.scheduled_time_hour.data = match.scheduled_time.time()
    
    return render_template('organizer/edit_match.html',
                           title='Edit Match',
                           tournament=tournament,
                           category=category,
                           match=match,
                           form=form)

@bp.route('/tournament/<int:id>/category/<int:category_id>/match/<int:match_id>/score', methods=['GET', 'POST'])
@login_required
@organizer_required
def edit_score(id, category_id, match_id):
    tournament = Tournament.query.get_or_404(id)
    category = TournamentCategory.query.get_or_404(category_id)
    match = Match.query.get_or_404(match_id)
    
    # Check if this tournament belongs to the current user
    if tournament.organizer_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to manage this tournament.', 'danger')
        return redirect(url_for('organizer.dashboard'))
    
    # Check if match belongs to this category
    if match.category_id != category_id:
        flash('Match not found in this category.', 'danger')
        return redirect(url_for('organizer.manage_category', id=id, category_id=category_id))
    
    form = ScoreForm()
    
    if form.validate_on_submit():
        # Check if this set already exists
        score = MatchScore.query.filter_by(
            match_id=match_id,
            set_number=form.set_number.data
        ).first()
        
        if score:
            # Update existing score
            score.player1_score = form.player1_score.data
            score.player2_score = form.player2_score.data
        else:
            # Create new score
            score = MatchScore(
                match_id=match_id,
                set_number=form.set_number.data,
                player1_score=form.player1_score.data,
                player2_score=form.player2_score.data
            )
            db.session.add(score)
        
        db.session.commit()
        
        flash('Score updated successfully!', 'success')
        return redirect(url_for('organizer.edit_score', id=id, category_id=category_id, match_id=match_id))
    
    # Get existing scores
    scores = MatchScore.query.filter_by(match_id=match_id).order_by(MatchScore.set_number).all()
    
    return render_template('organizer/edit_score.html',
                           title='Edit Match Score',
                           tournament=tournament,
                           category=category,
                           match=match,
                           form=form,
                           scores=scores)

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

