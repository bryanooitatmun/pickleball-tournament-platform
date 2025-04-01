from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user, login_required

from app import db
from app.organizer import bp  # Import the blueprint
from app.models import Tournament, TournamentCategory, Registration, Match
from app.decorators import organizer_required
from app.helpers.tournament import update_match_seeds

@bp.route('/tournament/<int:id>/category/<int:category_id>/manage_seeding', methods=['GET'])
@login_required
@organizer_required
def manage_seeding(id, category_id):
    """Route to display the seeding management page"""
    tournament = Tournament.query.get_or_404(id)
    category = TournamentCategory.query.get_or_404(category_id)
    
    # Permissions check
    if not current_user.is_admin() and tournament.organizer_id != current_user.id:
        flash('You do not have permission to manage this tournament.', 'danger')
        return redirect(url_for('main.tournament_detail', id=id))
    
    if category.tournament_id != tournament.id:
        flash('Category does not belong to this tournament.', 'danger')
        return redirect(url_for('organizer.tournament_detail', id=id))
    
    # Get registrations for this category
    registrations = Registration.query.filter_by(
        category_id=category_id, 
        is_approved=True
    ).order_by(Registration.seed.asc().nullslast(), Registration.registration_date).all()
    
    return render_template(
        'organizer/manage_tournament/manage_seeding.html',
        title=f"Manage Seeding - {category.name}",
        tournament=tournament,
        category=category,
        registrations=registrations
    )

@bp.route('/tournament/<int:id>/category/<int:category_id>/update_seeding', methods=['POST'])
@login_required
@organizer_required
def update_seeding(id, category_id):
    """AJAX endpoint to update seeds after drag and drop"""
    tournament = Tournament.query.get_or_404(id)
    category = TournamentCategory.query.get_or_404(category_id)
    
    # Permissions check
    if not current_user.is_admin() and tournament.organizer_id != current_user.id:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    
    if category.tournament_id != tournament.id:
        return jsonify({'success': False, 'message': 'Category does not belong to this tournament'}), 400
    
    try:
        # Get seed data from request
        seed_data = request.json.get('seeds', {})
        
        # Update seeds using the helper function
        success = update_match_seeds(category_id, seed_data)
        
        if success:
            return jsonify({'success': True, 'message': 'Seeds updated successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to update seeds'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500
