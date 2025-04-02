from flask import render_template, redirect, url_for, flash, request
from flask_login import current_user, login_required
from app import db
from app.admin import bp
from app.models import User, UserRole, Tournament, PlayerProfile, Match, TournamentStatus
from app.decorators import admin_required
import os
import sys
import subprocess

@bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # Get counts for dashboard metrics
    users_count = User.query.count()
    players_count = PlayerProfile.query.count()
    tournaments_count = Tournament.query.count()
    matches_count = Match.query.count()
    
    # Get newest users
    newest_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    
    # Get upcoming tournaments
    upcoming_tournaments = Tournament.query.filter_by(status='upcoming').order_by(Tournament.start_date).limit(5).all()
    
    return render_template('admin/dashboard.html',
                           title='Admin Dashboard',
                           users_count=users_count,
                           players_count=players_count,
                           tournaments_count=tournaments_count,
                           matches_count=matches_count,
                           newest_users=newest_users,
                           upcoming_tournaments=upcoming_tournaments)

@bp.route('/dev/seed', methods=['POST'])
@login_required
@admin_required
def run_seed():
    """Development-only route to run seed scripts"""
    if os.environ.get('FLASK_ENV') != 'development':
        flash('This feature is only available in development mode.', 'danger')
        return redirect(url_for('main.index'))
    
    if not current_user.is_admin():
        flash('Only admins can run seed scripts.', 'danger')
        return redirect(url_for('main.index'))
    
    seed_type = request.form.get('seed_type', 'all')
    cmd = [sys.executable, 'run_seeds.py', '--reset']
    
    if seed_type == 'users':
        cmd.append('--users-only')
    elif seed_type == 'tournament':
        cmd.append('--tournament-only')
    elif seed_type == 'mens_doubles':
        cmd.append('--mens-doubles')
    elif seed_type == 'womens_doubles':
        cmd.append('--womens-doubles')
    elif seed_type == 'no_brackets':
        cmd.append('--skip-brackets')
    elif seed_type == 'no_matches':
        cmd.append('--skip-matches')
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            flash(f'Seed script ran successfully: {seed_type}', 'success')
        else:
            flash(f'Error running seed script: {result.stderr}', 'danger')
    except Exception as e:
        flash(f'Error running seed script: {str(e)}', 'danger')
    
    return redirect(url_for('admin.dashboard'))

@bp.route('/users')
@login_required
@admin_required
def users():
    page = request.args.get('page', 1, type=int)
    users = User.query.paginate(page=page, per_page=20)
    
    return render_template('admin/users.html',
                           title='Manage Users',
                           users=users)

@bp.route('/user/<int:id>')
@login_required
@admin_required
def user_detail(id):
    user = User.query.get_or_404(id)
    
    # If user is player, get profile
    profile = None
    if user.role == UserRole.PLAYER:
        profile = PlayerProfile.query.filter_by(user_id=id).first()
    
    # If user is organizer, get tournaments
    tournaments = []
    if user.role == UserRole.ORGANIZER or user.role == UserRole.ADMIN:
        tournaments = Tournament.query.filter_by(organizer_id=id).all()
    
    return render_template('admin/user_detail.html',
                           title=f'User: {user.username}',
                           user=user,
                           profile=profile,
                           tournaments=tournaments)

@bp.route('/user/<int:id>/change_role', methods=['POST'])
@login_required
@admin_required
def change_role(id):
    user = User.query.get_or_404(id)
    
    # Prevent changing own role
    if user.id == current_user.id:
        flash('You cannot change your own role.', 'danger')
        return redirect(url_for('admin.user_detail', id=id))
    
    new_role = request.form.get('role')
    if new_role not in [role.name for role in UserRole]:
        flash('Invalid role selection.', 'danger')
        return redirect(url_for('admin.user_detail', id=id))
    
    user.role = UserRole[new_role]
    db.session.commit()
    
    flash(f'User role updated to {new_role}.', 'success')
    return redirect(url_for('admin.user_detail', id=id))

@bp.route('/user/<int:id>/toggle_active', methods=['POST'])
@login_required
@admin_required
def toggle_active(id):
    user = User.query.get_or_404(id)
    
    # Prevent deactivating own account
    if user.id == current_user.id:
        flash('You cannot deactivate your own account.', 'danger')
        return redirect(url_for('admin.user_detail', id=id))
    
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User account {status}.', 'success')
    return redirect(url_for('admin.user_detail', id=id))

@bp.route('/tournaments')
@login_required
@admin_required
def tournaments():
    page = request.args.get('page', 1, type=int)
    tournaments = Tournament.query.paginate(page=page, per_page=10)
    
    return render_template('admin/tournaments.html',
                           title='Manage Tournaments',
                           tournaments=tournaments)

@bp.route('/tournament/<int:id>')
@login_required
@admin_required
def tournament_detail(id):
    tournament = Tournament.query.get_or_404(id)
    
    # Get organizer
    organizer = User.query.get(tournament.organizer_id)
    
    # Get categories
    categories = tournament.categories.all()
    
    # Count registrations
    registration_counts = {}
    for category in categories:
        count = category.registrations.count()
        registration_counts[category.id] = count
    
    return render_template('admin/tournament_detail.html',
                           title=f'Tournament: {tournament.name}',
                           tournament=tournament,
                           organizer=organizer,
                           categories=categories,
                           registration_counts=registration_counts)

@bp.route('/players')
@login_required
@admin_required
def players():
    page = request.args.get('page', 1, type=int)
    players = PlayerProfile.query.join(User).filter(User.is_active == True).paginate(page=page, per_page=20)
    
    return render_template('admin/players.html',
                           title='Manage Players',
                           players=players)

@bp.route('/player/<int:id>')
@login_required
@admin_required
def player_detail(id):
    player = PlayerProfile.query.get_or_404(id)
    
    # Get user account
    user = User.query.get(player.user_id)
    
    # Get tournament registrations
    registrations = player.registrations.all()
    
    # Group registrations by tournament
    tournaments = {}
    for reg in registrations:
        tournament = reg.category.tournament
        if tournament.id not in tournaments:
            tournaments[tournament.id] = {
                'tournament': tournament,
                'categories': []
            }
        tournaments[tournament.id]['categories'].append(reg.category)
    
    return render_template('admin/player_detail.html',
                           title=f'Player: {player.full_name}',
                           player=player,
                           user=user,
                           tournaments=tournaments.values())

@bp.route('/system_stats')
@login_required
@admin_required
def system_stats():
    # User statistics
    total_users = User.query.count()
    players = User.query.filter_by(role=UserRole.PLAYER).count()
    organizers = User.query.filter_by(role=UserRole.ORGANIZER).count()
    admins = User.query.filter_by(role=UserRole.ADMIN).count()
    active_users = User.query.filter_by(is_active=True).count()
    inactive_users = User.query.filter_by(is_active=False).count()
    
    # Tournament statistics
    total_tournaments = Tournament.query.count()
    upcoming_tournaments = Tournament.query.filter_by(status='upcoming').count()
    ongoing_tournaments = Tournament.query.filter_by(status='ongoing').count()
    completed_tournaments = Tournament.query.filter_by(status='completed').count()
    
    # Match statistics
    total_matches = Match.query.count()
    completed_matches = Match.query.filter_by(completed=True).count()
    
    return render_template('admin/system_stats.html',
                           title='System Statistics',
                           user_stats={
                               'total': total_users,
                               'players': players,
                               'organizers': organizers,
                               'admins': admins,
                               'active': active_users,
                               'inactive': inactive_users
                           },
                           tournament_stats={
                               'total': total_tournaments,
                               'upcoming': upcoming_tournaments,
                               'ongoing': ongoing_tournaments,
                               'completed': completed_tournaments
                           },
                           match_stats={
                               'total': total_matches,
                               'completed': completed_matches
                           })
