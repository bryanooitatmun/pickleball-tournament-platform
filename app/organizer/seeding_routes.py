from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user, login_required

from app import db
from app.organizer import bp  # Import the blueprint
from app.models import Tournament, TournamentCategory, Registration, Match
from app.decorators import organizer_required
from app.helpers.tournament import update_match_seeds

@bp.route('/tournament/<int:tournament_id>/category/<int:category_id>/seeding', methods=['GET', 'POST'])
@login_required
@organizer_required
def manage_seeding(tournament_id, category_id):
    """Manage seeding for a specific tournament category."""
    tournament = Tournament.query.get_or_404(tournament_id)
    category = TournamentCategory.query.get_or_404(category_id)

    # Permissions check
    if not current_user.is_admin() and tournament.organizer_id != current_user.id:
        flash('You do not have permission to manage seeding for this tournament.', 'danger')
        return redirect(url_for('organizer.tournament_detail', id=tournament_id))
    if category.tournament_id != tournament.id:
         flash('Category does not belong to this tournament.', 'danger')
         return redirect(url_for('organizer.tournament_detail', id=tournament_id))

    if request.method == 'POST':
        # Handle AJAX request to update seeds
        seed_data = request.get_json()
        if not seed_data or not isinstance(seed_data, list):
            return jsonify({'success': False, 'message': 'Invalid data format.'}), 400

        try:
            success = update_match_seeds(category_id, seed_data)
            if success:
                return jsonify({'success': True, 'message': 'Seeding updated successfully.'})
            else:
                # update_match_seeds might return False for validation errors handled internally
                return jsonify({'success': False, 'message': 'Failed to update seeding. Check data.'}), 400
        except Exception as e:
            current_app.logger.error(f"Error updating seeds for category {category_id}: {e}")
            db.session.rollback()
            return jsonify({'success': False, 'message': f'An internal error occurred: {e}'}), 500

    # --- GET Request Logic ---
    # Fetch approved registrations, ordered by current seed (nulls last), then registration date
    registrations = Registration.query.filter_by(
        category_id=category_id,
        is_approved=True
    ).order_by(
        Registration.seed.asc().nullslast(),
        Registration.registration_date.asc()
    ).all()

    return render_template('organizer/manage_tournament/manage_seeding.html', # New template needed
                          title=f"Manage Seeding - {category.name}",
                          tournament=tournament,
                          category=category,
                          registrations=registrations)

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
