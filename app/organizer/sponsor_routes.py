import os
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import current_user, login_required

from app import db
from app.organizer import bp # Import the blueprint
from app.organizer.forms import SponsorForm, TournamentSponsorForm # Import relevant forms
# Import necessary models using the new structure
from app.models import Tournament, PlatformSponsor, SponsorTier
from app.decorators import organizer_required
from app.helpers.registration import save_picture # Assuming this helper handles image saving

# --- Standalone Sponsor Management ---
@bp.route('/tournament/<int:id>/sponsors', methods=['GET', 'POST'])
@login_required
@organizer_required
def edit_sponsors(id):
    """Edit sponsors for a tournament"""
    tournament = Tournament.query.get_or_404(id)
    
    # Ensure the tournament belongs to this organizer
    if tournament.organizer_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to edit this tournament.', 'danger')
        return redirect(url_for('organizer.dashboard'))
    
    form = TournamentSponsorForm()
    
    if form.validate_on_submit():
        # Get selected sponsor IDs and order
        sponsor_ids = request.form.getlist('selected_sponsors')
        sponsor_order = request.form.getlist('sponsor_order[]')
        
        # Clear existing sponsors
        tournament.platform_sponsors = []
        
        # Add selected sponsors in order
        if sponsor_ids:
            # First process sponsors with defined order
            for sponsor_id in sponsor_order:
                if sponsor_id in sponsor_ids:
                    sponsor = PlatformSponsor.query.get(sponsor_id)
                    if sponsor:
                        tournament.platform_sponsors.append(sponsor)
            
            # Then add any remaining sponsors that were checked but not in the order list
            for sponsor_id in sponsor_ids:
                if sponsor_id not in sponsor_order:
                    sponsor = PlatformSponsor.query.get(sponsor_id)
                    if sponsor:
                        tournament.platform_sponsors.append(sponsor)
        
        db.session.commit()
        flash('Tournament sponsors updated successfully.', 'success')
        return redirect(url_for('organizer.edit_tournament', id=id))
    
    # Get all sponsors for selection
    all_sponsors = PlatformSponsor.query.order_by(
        # Order by tier first (Premier > Official > Featured > Supporting)
        db.case(
            {
                'PREMIER': 1,
                'OFFICIAL': 2,
                'FEATURED': 3,
                'SUPPORTING': 4
            },
            value=PlatformSponsor.tier.name,
            else_=5
        ),
        # Then by display order within tier
        PlatformSponsor.display_order
    ).all()
    
    # Get currently selected sponsor IDs
    selected_sponsor_ids = [sponsor.id for sponsor in tournament.platform_sponsors]
    
    # Get tournament sponsors in their current order
    tournament_sponsors = tournament.platform_sponsors

    print(tournament_sponsors)

    # Sort the sponsors by tier first, then by display_order
    tournament_sponsors = sorted(tournament_sponsors, 
        key=lambda x: (
            # Order by tier priority (Premier > Official > Featured > Supporting)
            {'PREMIER': 1, 'OFFICIAL': 2, 'FEATURED': 3, 'SUPPORTING': 4}.get(x.tier.name if x.tier else 'SUPPORTING', 5),
            # Then by display order within tier
            x.display_order or 999
        )
    )
    print(tournament_sponsors)
    # Available sponsors (excluding already selected)
    available_sponsors = all_sponsors
    
    return render_template('organizer/edit_sponsors.html',
                          title='Edit Sponsors',
                          tournament=tournament,
                          available_sponsors=available_sponsors,
                          selected_sponsor_ids=selected_sponsor_ids,
                          tournament_sponsors=tournament_sponsors,
                          form=form)

@bp.route('/sponsors')
@login_required
@organizer_required # Or admin_required depending on who manages global sponsors
def manage_sponsors():
    """List all platform sponsors"""
    # Define tier order for sorting
    tier_order = {
        SponsorTier.PREMIER: 1,
        SponsorTier.OFFICIAL: 2,
        SponsorTier.FEATURED: 3,
        SponsorTier.SUPPORTING: 4
    }
    sponsors = PlatformSponsor.query.all()
    # Sort in Python after fetching
    sponsors.sort(key=lambda s: (tier_order.get(s.tier, 5), s.display_order or 999, s.name))

    return render_template('organizer/edit_tournament/manage_sponsors.html', # Consider moving templates
                          title='Manage Sponsors',
                          sponsors=sponsors)

@bp.route('/sponsor/create', methods=['GET', 'POST'])
@login_required
@organizer_required # Or admin_required
def create_sponsor():
    """Create a new platform sponsor"""
    form = SponsorForm()
    if form.validate_on_submit():
        tier = SponsorTier[form.tier.data] if form.tier.data else SponsorTier.SUPPORTING

        sponsor = PlatformSponsor(
            name=form.name.data,
            tier=tier,
            description=form.description.data,
            website=form.website.data,
            is_featured=form.is_featured.data,
            display_order=form.display_order.data or 999,
            contact_name=form.contact_name.data,
            contact_email=form.contact_email.data,
            contact_phone=form.contact_phone.data
        )

        # Handle image uploads
        if form.logo.data:
            sponsor.logo = save_picture(form.logo.data, 'sponsor_logos')
        if form.banner_image.data:
            sponsor.banner_image = save_picture(form.banner_image.data, 'sponsor_banners')

        try:
            db.session.add(sponsor)
            db.session.commit()
            flash('Sponsor created successfully!', 'success')
            return redirect(url_for('organizer.manage_sponsors'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating sponsor: {e}', 'danger')

    return render_template('organizer/edit_tournament/create_sponsor.html', # Consider moving templates
                          title='Create Sponsor',
                          form=form)

@bp.route('/sponsor/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@organizer_required # Or admin_required
def edit_sponsor(id):
    """Edit sponsor details"""
    sponsor = PlatformSponsor.query.get_or_404(id)
    form = SponsorForm(obj=sponsor)

    # Pre-select tier for GET request
    if request.method == 'GET' and sponsor.tier:
        form.tier.data = sponsor.tier.name

    if form.validate_on_submit():
        form.populate_obj(sponsor) # Populate basic fields
        sponsor.tier = SponsorTier[form.tier.data] if form.tier.data else SponsorTier.SUPPORTING
        sponsor.display_order = form.display_order.data or 999

        # Handle image uploads only if new files are provided
        if form.logo.data and hasattr(form.logo.data, 'filename'):
            sponsor.logo = save_picture(form.logo.data, 'sponsor_logos')
        if form.banner_image.data and hasattr(form.banner_image.data, 'filename'):
            sponsor.banner_image = save_picture(form.banner_image.data, 'sponsor_banners')

        try:
            db.session.commit()
            flash('Sponsor updated successfully!', 'success')
            return redirect(url_for('organizer.manage_sponsors'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating sponsor: {e}', 'danger')

    return render_template('organizer/edit_tournament/edit_sponsor.html', # Consider moving templates
                          title=f'Edit Sponsor: {sponsor.name}',
                          sponsor=sponsor,
                          form=form)

@bp.route('/sponsor/<int:id>/delete', methods=['POST'])
@login_required
@organizer_required # Or admin_required
def delete_sponsor(id):
    """Delete a platform sponsor"""
    sponsor = PlatformSponsor.query.get_or_404(id)

    try:
        # Note: The relationship via secondary table should handle dissociation automatically
        # If cascade options are set correctly. If not, manually remove associations:
        # sponsor.tournaments.clear()

        # Delete image files (add error handling)
        if sponsor.logo:
            logo_path = os.path.join(current_app.config['UPLOAD_FOLDER'], sponsor.logo.split('/')[-1]) # Adjust path logic
            if os.path.exists(logo_path): os.remove(logo_path)
        if sponsor.banner_image:
            banner_path = os.path.join(current_app.config['UPLOAD_FOLDER'], sponsor.banner_image.split('/')[-1]) # Adjust path logic
            if os.path.exists(banner_path): os.remove(banner_path)

        db.session.delete(sponsor)
        db.session.commit()
        flash('Sponsor deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting sponsor: {e}. Check if it is linked to prizes.', 'danger') # Prizes might have FK constraint

    return redirect(url_for('organizer.manage_sponsors'))


# --- Tournament-Specific Sponsor Assignment ---

@bp.route('/tournament/<int:id>/sponsors', methods=['GET', 'POST'])
@login_required
@organizer_required
def edit_tournament_sponsors(id):
    """Assign or change sponsors for a specific tournament"""
    tournament = Tournament.query.get_or_404(id)

    # Check permission
    if not current_user.is_admin() and tournament.organizer_id != current_user.id:
        flash('You do not have permission to edit sponsors for this tournament.', 'danger')
        return redirect(url_for('organizer.tournament_detail', id=id))

    form = TournamentSponsorForm() # This form might just be for CSRF token

    if request.method == 'POST':
        try:
            # Get selected sponsor IDs from the form submission
            selected_ids = set(request.form.getlist('selected_sponsors')) # Use set for efficient lookup

            # Get current sponsors associated with the tournament
            current_sponsors = set(tournament.platform_sponsors)
            current_sponsor_ids = {s.id for s in current_sponsors}

            # Find sponsors to add and remove
            ids_to_add = selected_ids - current_sponsor_ids
            ids_to_remove = current_sponsor_ids - selected_ids

            # Add new sponsors
            for sponsor_id_str in ids_to_add:
                sponsor_id = int(sponsor_id_str)
                sponsor = PlatformSponsor.query.get(sponsor_id)
                if sponsor:
                    tournament.platform_sponsors.append(sponsor)

            # Remove deselected sponsors
            for sponsor_id_str in ids_to_remove:
                 sponsor_id = int(sponsor_id_str)
                 sponsor = PlatformSponsor.query.get(sponsor_id)
                 if sponsor in current_sponsors: # Check if actually associated before removing
                      tournament.platform_sponsors.remove(sponsor)

            db.session.commit()
            flash('Tournament sponsors updated successfully.', 'success')
            # Redirect back to the main tournament edit page or detail page
            return redirect(url_for('organizer.edit_tournament', id=id))
        except ValueError:
             flash('Invalid sponsor ID submitted.', 'danger')
             db.session.rollback()
        except Exception as e:
            flash(f'Error updating tournament sponsors: {e}', 'danger')
            db.session.rollback()


    # --- GET Request Logic ---
    # Get all available platform sponsors, ordered for display
    tier_order = { SponsorTier.PREMIER: 1, SponsorTier.OFFICIAL: 2, SponsorTier.FEATURED: 3, SponsorTier.SUPPORTING: 4 }
    all_sponsors = PlatformSponsor.query.all()
    all_sponsors.sort(key=lambda s: (tier_order.get(s.tier, 5), s.display_order or 999, s.name))

    # Get IDs of sponsors currently associated with this tournament
    selected_sponsor_ids = {sponsor.id for sponsor in tournament.platform_sponsors}

    return render_template('organizer/edit_tournament/edit_tournament_sponsors.html', # Consider moving templates
                          title=f'Edit Sponsors for {tournament.name}',
                          tournament=tournament,
                          all_sponsors=all_sponsors,
                          selected_sponsor_ids=selected_sponsor_ids,
                          form=form) # Pass CSRF form