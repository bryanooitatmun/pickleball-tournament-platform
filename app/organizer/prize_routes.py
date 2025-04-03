from flask import render_template, redirect, url_for, flash, request
from flask_login import current_user, login_required

from app import db
from app.organizer import bp # Import the blueprint
# Import necessary models using the new structure
from app.models import Tournament, TournamentCategory, Prize, PrizeType
from app.decorators import organizer_required
from app.services import PrizeService # Assuming PrizeService exists for distribution

@bp.route('/tournament/<int:id>/edit/prizes', methods=['GET', 'POST'])
@login_required
@organizer_required
def edit_prizes(id):
    tournament = Tournament.query.get_or_404(id)

    # Check permission
    if not current_user.is_admin() and tournament.organizer_id != current_user.id:
        flash('You do not have permission to edit prizes for this tournament.', 'danger')
        return redirect(url_for('organizer.tournament_detail', id=tournament.id))

    categories = tournament.categories.order_by(TournamentCategory.display_order).all()

    if request.method == 'POST':
        try:
            # Process prize updates for each category
            for category in categories:
                # --- Update existing prizes ---
                existing_prize_ids = request.form.getlist(f'prize_id_{category.id}')
                for prize_id_str in existing_prize_ids:
                    prize_id = int(prize_id_str)
                    prize = Prize.query.get(prize_id)
                    if prize and prize.category_id == category.id:
                        prize.prize_type = PrizeType(request.form.get(f'prize_type_{prize_id}'))
                        prize.placement = request.form.get(f'placement_{prize_id}')

                        if prize.prize_type == PrizeType.CASH:
                            prize.cash_amount = float(request.form.get(f'cash_amount_{prize_id}', 0.0))
                            # Clear non-cash fields
                            prize.title = None
                            prize.description = None
                            prize.monetary_value = None
                            prize.quantity = None
                            prize.vendor = None
                            prize.expiry_date = None
                            prize.sponsor_id = None
                        elif prize.prize_type == PrizeType.MERCHANDISE:
                            prize.title = request.form.get(f'title_{prize_id}', '')
                            prize.description = request.form.get(f'description_{prize_id}', '')
                            prize.monetary_value = float(request.form.get(f'monetary_value_{prize_id}', 0.0))
                            prize.quantity = int(request.form.get(f'quantity_{prize_id}', 1))
                            # Clear cash fields
                            prize.cash_amount = None
                            # TODO: Handle image upload for existing prizes if needed

                # --- Process new prizes ---
                new_prize_placements = request.form.getlist(f'new_placement_{category.id}')
                for i, placement in enumerate(new_prize_placements):
                    if placement.strip(): # Only process if placement is not empty
                        prize_type = PrizeType(request.form.getlist(f'new_prize_type_{category.id}')[i])
                        new_prize = Prize(category_id=category.id, placement=placement, prize_type=prize_type)

                        if prize_type == PrizeType.CASH:
                            new_prize.cash_amount = float(request.form.getlist(f'new_cash_amount_{category.id}')[i] or 0.0)
                        elif prize_type == PrizeType.MERCHANDISE:
                            new_prize.title = request.form.getlist(f'new_title_{category.id}')[i] or ''
                            new_prize.description = request.form.getlist(f'new_description_{category.id}')[i] or ''
                            new_prize.monetary_value = float(request.form.getlist(f'new_monetary_value_{category.id}')[i] or 0.0)
                            new_prize.quantity = int(request.form.getlist(f'new_quantity_{category.id}')[i] or 1)
                            # TODO: Handle image upload for new prizes if needed

                        db.session.add(new_prize)

                # --- Process prize deletions ---
                for prize_id_str in request.form.getlist(f'delete_prize_{category.id}'):
                    prize_id = int(prize_id_str)
                    prize = Prize.query.get(prize_id)
                    if prize and prize.category_id == category.id:
                        db.session.delete(prize)

            # --- Commit and Finalize ---
            db.session.commit() # Commit all prize changes first

            # Update category flags and totals after commit
            for category in categories:
                category.calculate_prize_values() # Recalculate based on new prize objects

            # Update tournament totals based on updated categories
            tournament.total_cash_prize = sum(cat.prize_money or 0.0 for cat in categories)
            tournament.total_prize_value = sum(cat.total_prize_value or 0.0 for cat in categories)
            tournament.prize_pool = tournament.total_prize_value
            db.session.commit() # Commit updated totals

            flash('Tournament prizes updated successfully!', 'success')
            # Redirect back to tournament management or detail page
            return redirect(url_for('organizer.tournament_detail', id=tournament.id))

        except ValueError as e:
             flash(f'Invalid input for prizes: {e}', 'danger')
             db.session.rollback()
        except Exception as e:
            flash(f'An error occurred while saving prize changes: {e}', 'danger')
            db.session.rollback()

    # --- Render Template for GET or after error ---
    prize_data = {}
    for category in categories:
        # Eager load prizes to avoid N+1 queries in template
        prize_data[category.id] = Prize.query.filter_by(category_id=category.id).order_by(Prize.placement).all()

    return render_template(
        'organizer/edit_prizes.html',
        title=f'Edit Prizes - {tournament.name}',
        tournament=tournament,
        categories=categories,
        prize_data=prize_data,
        prize_types=[(pt.value, pt.name.capitalize()) for pt in PrizeType] # Pass enum values for dropdowns
    )


@bp.route('/tournament/<int:id>/distribute_prize_money', methods=['POST'])
@login_required
@organizer_required
def distribute_prize_money(id):
    """Distribute prize money across categories based on percentages"""
    tournament = Tournament.query.get_or_404(id)

    # Check permission
    if not current_user.is_admin() and tournament.organizer_id != current_user.id:
        flash('You do not have permission to manage this tournament.', 'danger')
        return redirect(url_for('organizer.tournament_detail', id=id))

    if tournament.prize_pool is None or tournament.prize_pool <= 0:
         flash('Tournament prize pool must be set to distribute prize money.', 'warning')
         return redirect(url_for('organizer.edit_prizes', id=id))

    try:
        # Use PrizeService (or implement logic here)
        updated_categories = PrizeService.distribute_prize_pool(tournament.id) # Assumes service handles commit
        flash(f'Prize money distributed among {len(updated_categories)} categories based on percentages.', 'success')
    except Exception as e:
        flash(f'Error distributing prize money: {e}', 'danger')
        db.session.rollback() # Ensure rollback if service doesn't handle it

    # Redirect to prize editing page to see results
    return redirect(url_for('organizer.edit_prizes', id=id))