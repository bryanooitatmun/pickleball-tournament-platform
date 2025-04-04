from flask import render_template, redirect, url_for, flash, request
from flask_login import current_user, login_required

from app import db
from app.organizer import bp # Import the blueprint
# Import necessary models using the new structure
from app.models import (Tournament, TournamentCategory, Registration, Match, Group,
                       CategoryType, TournamentFormat, TournamentStatus)
from app.decorators import organizer_required, referee_or_organizer_required
# Import helpers if needed for bracket generation logic called from here
from app.helpers.tournament import (
    _generate_group_stage,
    _generate_knockout_from_groups,
    _generate_single_elimination,
    update_match_seeds # Import the helper for updating seeds
)
from flask import jsonify # Import jsonify for POST response

@bp.route('/tournament/<int:id>/edit/categories', methods=['GET', 'POST'])
@login_required
@organizer_required
def edit_categories(id):
    tournament = Tournament.query.get_or_404(id)

    # Check permission
    if not current_user.is_admin() and tournament.organizer_id != current_user.id:
        flash('You do not have permission to edit categories for this tournament.', 'danger')
        return redirect(url_for('organizer.tournament_detail', id=tournament.id))

    # Get existing categories for display
    categories = tournament.categories.order_by(TournamentCategory.display_order).all()

    if request.method == 'POST':
        updated_category_ids = []
        new_categories_added = False

        # --- Process existing categories ---
        for category_id_str in request.form.getlist('category_id'):
            try:
                category_id = int(category_id_str)
                category = TournamentCategory.query.get(category_id)
                if category and category.tournament_id == tournament.id:
                    updated_category_ids.append(category.id)
                    # Update fields
                    category.name = request.form.get(f'name_{category_id}')
                    category.category_type = CategoryType(request.form.get(f'category_type_{category_id}'))
                    category.max_participants = int(request.form.get(f'max_participants_{category_id}', 0))
                    category.points_awarded = int(request.form.get(f'points_awarded_{category_id}', 0))
                    # Use tournament format if category format is not specified or invalid
                    cat_format_val = request.form.get(f'format_{category_id}')
                    category.format = TournamentFormat(cat_format_val) if cat_format_val else tournament.format
                    category.registration_fee = float(request.form.get(f'registration_fee_{category_id}', 0.0))
                    category.description = request.form.get(f'description_{category_id}', '')
                    category.display_order = int(request.form.get(f'display_order_{category_id}', 999))
                    
                    # prize_percentage and prize_money are now calculated values, don't update from form

                    # Optional restriction fields
                    min_dupr = request.form.get(f'min_dupr_rating_{category_id}', '')
                    max_dupr = request.form.get(f'max_dupr_rating_{category_id}', '')
                    min_age = request.form.get(f'min_age_{category_id}', '')
                    max_age = request.form.get(f'max_age_{category_id}', '')
                    gender = request.form.get(f'gender_restriction_{category_id}', '')

                    category.min_dupr_rating = float(min_dupr) if min_dupr else None
                    category.max_dupr_rating = float(max_dupr) if max_dupr else None
                    category.min_age = int(min_age) if min_age else None
                    category.max_age = int(max_age) if max_age else None
                    category.gender_restriction = gender if gender else None

            except ValueError as e:
                flash(f'Invalid input for category {category_id}: {e}', 'danger')
                # Consider how to handle partial failures - rollback or continue?
            except Exception as e:
                 flash(f'Error updating category {category_id}: {e}', 'danger')


        # --- Process new categories ---
        new_category_names = request.form.getlist('new_category_name')
        for i, name in enumerate(new_category_names):
            if name.strip(): # Only process if name is not empty
                try:
                    new_cat = TournamentCategory(
                        tournament_id=tournament.id,
                        name=name,
                        category_type=CategoryType(request.form.getlist('new_category_type')[i]),
                        max_participants=int(request.form.getlist('new_max_participants')[i] or 0),
                        points_awarded=int(request.form.getlist('new_points_awarded')[i] or 0),
                        # Use tournament format if category format is not specified or invalid
                        format=TournamentFormat(request.form.getlist('new_format')[i]) if request.form.getlist('new_format')[i] else tournament.format,
                        registration_fee=float(request.form.getlist('new_registration_fee')[i] or 0.0),
                        description=request.form.getlist('new_description')[i] or '',
                        display_order=int(request.form.getlist('new_display_order')[i] or 999),
                        # prize_percentage and prize_money will be calculated later
                    )

                    # Optional restriction fields for new categories
                    min_dupr = request.form.getlist('new_min_dupr_rating')[i]
                    max_dupr = request.form.getlist('new_max_dupr_rating')[i]
                    min_age = request.form.getlist('new_min_age')[i]
                    max_age = request.form.getlist('new_max_age')[i]
                    gender = request.form.getlist('new_gender_restriction')[i]

                    new_cat.min_dupr_rating = float(min_dupr) if min_dupr else None
                    new_cat.max_dupr_rating = float(max_dupr) if max_dupr else None
                    new_cat.min_age = int(min_age) if min_age else None
                    new_cat.max_age = int(max_age) if max_age else None
                    new_cat.gender_restriction = gender if gender else None

                    db.session.add(new_cat)
                    new_categories_added = True
                except ValueError as e:
                    flash(f'Invalid input for new category "{name}": {e}', 'danger')
                except Exception as e:
                    flash(f'Error adding new category "{name}": {e}', 'danger')


        # --- Process category deletions ---
        deleted_category_names = []
        for category_id_str in request.form.getlist('delete_category'):
            try:
                category_id = int(category_id_str)
                category = TournamentCategory.query.get(category_id)
                if category and category.tournament_id == tournament.id:
                    # Check if registrations exist before deleting
                    if category.registrations.count() > 0:
                        flash(f'Cannot delete category "{category.name}" because it has registrations.', 'warning')
                    else:
                        deleted_category_names.append(category.name)
                        db.session.delete(category)
            except ValueError:
                 flash(f'Invalid category ID for deletion: {category_id_str}', 'danger')
            except Exception as e:
                 flash(f'Error deleting category {category_id_str}: {e}', 'danger')


        # --- Commit and Finalize ---
        try:
            db.session.commit()
            flash_messages = []
            if updated_category_ids:
                flash_messages.append(f'Updated {len(updated_category_ids)} categories.')
            if new_categories_added:
                 flash_messages.append('Added new categories.')
            if deleted_category_names:
                 flash_messages.append(f'Deleted categories: {", ".join(deleted_category_names)}.')

            if not flash_messages:
                 flash_messages.append('No changes detected.')

            flash(' '.join(flash_messages), 'success')

            # Recalculate prize values for all remaining categories after commit
            # This might be better in a service or triggered separately
            remaining_categories = TournamentCategory.query.filter_by(tournament_id=tournament.id).all()
            total_cash = 0.0
            total_value = 0.0
            for category in remaining_categories:
                category.calculate_prize_values() # This method needs refinement (see model)
                total_cash += category.prize_money or 0.0
                total_value += category.total_prize_value or 0.0

            tournament.total_cash_prize = total_cash
            tournament.total_prize_value = total_value
            db.session.commit() # Commit again after calculations

            # Redirect to prize editing or back to tournament detail
            return redirect(url_for('organizer.edit_prizes', id=tournament.id))

        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while saving category changes: {e}', 'danger')
            # Reload categories from DB state before rollback
            categories = tournament.categories.order_by(TournamentCategory.display_order).all()


    # --- Render Template for GET or after error ---
    return render_template(
        'organizer/edit_categories.html',
        title=f'Edit Categories - {tournament.name}',
        tournament=tournament,
        categories=categories,
        # Pass enum values for dropdowns
        category_types=[(ct.value, ct.value) for ct in CategoryType],
        tournament_formats=[(tf.value, tf.value) for tf in TournamentFormat]
    )


@bp.route('/tournament/<int:id>/manage_category/<int:category_id>', methods=['GET', 'POST'])
@login_required
@referee_or_organizer_required
def manage_category(id, category_id):
    tournament = Tournament.query.get_or_404(id)
    category = TournamentCategory.query.get_or_404(category_id)

    # Check if user is referee only (not also an organizer or admin)
    is_referee_only = current_user.is_referee() and not current_user.is_organizer() and not current_user.is_admin()

    # Permissions check for non-referees
    if not is_referee_only and not current_user.is_admin() and tournament.organizer_id != current_user.id:
        flash('You do not have permission to manage this tournament.', 'danger')
        return redirect(url_for('main.tournament_detail', id=id)) # Redirect to public view
    if category.tournament_id != tournament.id:
         flash('Category does not belong to this tournament.', 'danger')
         return redirect(url_for('organizer.tournament_detail', id=id))

    if request.method == 'POST':
        action = request.form.get('action')

        # --- Update Category Settings ---
        if action == 'update_settings':
            try:
                category.max_participants = int(request.form.get('max_participants', category.max_participants or 0))
                category.points_awarded = int(request.form.get('points_awarded', category.points_awarded or 0))
                # prize_percentage is now a calculated value, don't update from form

                min_dupr = request.form.get('min_dupr_rating', '')
                max_dupr = request.form.get('max_dupr_rating', '')
                min_age = request.form.get('min_age', '')
                max_age = request.form.get('max_age', '')
                gender = request.form.get('gender_restriction', '')

                category.min_dupr_rating = float(min_dupr) if min_dupr else None
                category.max_dupr_rating = float(max_dupr) if max_dupr else None
                category.min_age = int(min_age) if min_age else None
                category.max_age = int(max_age) if max_age else None
                category.gender_restriction = gender if gender else None

                # Format-specific settings (only if applicable)
                if tournament.format == TournamentFormat.GROUP_KNOCKOUT:
                    category.group_count = int(request.form.get('group_count', category.group_count or 0))
                    category.teams_advancing_per_group = int(request.form.get('teams_advancing_per_group', category.teams_advancing_per_group or 0))

                db.session.commit()
                flash('Category settings updated successfully.', 'success')
            except ValueError as e:
                 flash(f'Invalid input for settings: {e}', 'danger')
                 db.session.rollback()
            except Exception as e:
                 flash(f'Error updating settings: {e}', 'danger')
                 db.session.rollback()

        # --- Update Prize Distribution ---
        elif action == 'update_prize_distribution':
            try:
                prize_distribution = {}
                total_percentage = 0.0
                for key in request.form:
                    if key.startswith('prize_'):
                        place_range = key[6:] # Remove 'prize_' prefix
                        percentage_str = request.form.get(key, '')
                        if percentage_str:
                            percentage = float(percentage_str)
                            if percentage < 0: raise ValueError("Percentage cannot be negative.")
                            prize_distribution[place_range] = percentage
                            total_percentage += percentage

                # Basic validation (can be more complex)
                if abs(total_percentage - 100.0) > 0.01 and total_percentage != 0.0: # Allow 0 or 100
                    flash('Prize distribution percentages should ideally add up to 100%.', 'warning')
                    # Decide whether to save anyway or force correction

                category.prize_distribution = prize_distribution
                db.session.commit()
                flash('Prize distribution updated successfully.', 'success')
            except ValueError as e:
                 flash(f'Invalid input for prize distribution: {e}', 'danger')
                 db.session.rollback()
            except Exception as e:
                 flash(f'Error updating prize distribution: {e}', 'danger')
                 db.session.rollback()

        # --- Update Points Distribution ---
        elif action == 'update_points_distribution':
            try:
                points_distribution = {}
                for key in request.form:
                    if key.startswith('points_'):
                        place_range = key[7:] # Remove 'points_' prefix
                        percentage_str = request.form.get(key, '')
                        if percentage_str:
                             percentage = float(percentage_str)
                             if percentage < 0: raise ValueError("Percentage cannot be negative.")
                             points_distribution[place_range] = percentage

                category.points_distribution = points_distribution
                db.session.commit()
                flash('Points distribution updated successfully.', 'success')
            except ValueError as e:
                 flash(f'Invalid input for points distribution: {e}', 'danger')
                 db.session.rollback()
            except Exception as e:
                 flash(f'Error updating points distribution: {e}', 'danger')
                 db.session.rollback()

        # --- Generate Bracket ---
        elif action == 'generate_bracket':
            category.group_count = int(request.form.get('group_count', category.group_count or 4))
            category.teams_per_group = int(request.form.get('teams_per_group', category.teams_per_group or 4))
            category.teams_advancing_per_group = int(request.form.get('teams_advancing_per_group', category.teams_advancing_per_group or 2))
            bracket_type = request.form.get('bracket_type') # e.g., 'generate_groups', 'generate_knockout'
            success = False
            message = "Bracket generation failed."
            try:
                if bracket_type == 'generate_groups' and tournament.format == TournamentFormat.GROUP_KNOCKOUT:
                    success = _generate_group_stage(category)
                    message = 'Group stage generated successfully.' if success else 'Failed to generate group stage.'
                elif bracket_type == 'generate_knockout':
                    if tournament.format == TournamentFormat.GROUP_KNOCKOUT:
                        success = _generate_knockout_from_groups(category)
                        message = 'Knockout bracket generated from groups successfully.' if success else 'Failed to generate knockout from groups.'
                    elif tournament.format == TournamentFormat.SINGLE_ELIMINATION:
                        use_seeding = request.form.get('use_seeding') == 'on'
                        third_place = request.form.get('third_place_match') == 'on'
                        success = _generate_single_elimination(category, use_seeding=use_seeding, third_place_match=third_place)
                        message = 'Single elimination bracket generated successfully.' if success else 'Failed to generate single elimination bracket.'
                    # Add other formats like Double Elimination if implemented
                    else:
                         message = f"Bracket generation not applicable for format: {tournament.format.value}"
                else:
                    message = 'Invalid bracket type or format mismatch.'

                flash(message, 'success' if success else 'danger')

            except Exception as e:
                 flash(f'Error during bracket generation: {e}', 'danger')
                 db.session.rollback() # Rollback any partial bracket creation

        # Redirect back to the same page after POST action
        return redirect(url_for('organizer.manage_category', id=id, category_id=category_id))

    # --- GET Request Logic ---
    # Get data needed for the manage category page
    registrations = Registration.query.filter_by(category_id=category_id, is_approved=True).order_by(Registration.seed.asc().nullslast(), Registration.registration_date).all() # Show approved for seeding/brackets
    matches = Match.query.filter_by(category_id=category_id).order_by(Match.stage, Match.round, Match.match_order).all()
    groups = Group.query.filter_by(category_id=category_id).order_by(Group.name).all()

    # Prepare data for prize/points distribution forms (example structure)
    default_placements = ["1", "2", "3-4", "5-8", "9-16"] # Example default placements
    prize_dist_data = {p: category.prize_distribution.get(p) for p in default_placements}
    points_dist_data = {p: category.points_distribution.get(p) for p in default_placements}

    return render_template('organizer/manage_tournament/manage_category.html', # Assuming template exists
                          title=f"Manage {category.name}",
                          tournament=tournament,
                          category=category,
                          registrations=registrations,
                          matches=matches,
                          groups=groups,
                          prize_dist_data=prize_dist_data,
                          points_dist_data=points_dist_data,
                          default_placements=default_placements,
                          is_referee_only=is_referee_only)
