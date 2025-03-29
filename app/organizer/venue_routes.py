import os
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import current_user, login_required

from app import db
from app.organizer import bp # Import the blueprint
from app.organizer.forms import VenueForm, VenueImageForm, TournamentVenueForm # Import relevant forms
# Import necessary models using the new structure
from app.models import Tournament, Venue, VenueImage
from app.decorators import organizer_required
from app.helpers.registration import save_picture # Assuming this helper handles image saving

# --- Standalone Venue Management ---
@bp.route('/tournament/<int:id>/venue', methods=['GET', 'POST'])
@login_required
@organizer_required
def edit_venue(id):
    """Edit venue for a tournament"""
    tournament = Tournament.query.get_or_404(id)
    
    # Ensure the tournament belongs to this organizer
    if tournament.organizer_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to edit this tournament.', 'danger')
        return redirect(url_for('organizer.dashboard'))
    
    form = TournamentVenueForm()
    
    if form.validate_on_submit():
        venue_id = form.venue_id.data
        if venue_id:
            venue = Venue.query.get(venue_id)
            if venue:
                tournament.venue_id = venue_id
            else:
                flash('Selected venue not found.', 'danger')
        else:
            tournament.venue_id = None
            
        db.session.commit()
        flash('Tournament venue updated successfully.', 'success')
        return redirect(url_for('organizer.edit_tournament', id=id))
    
    # Get all venues for dropdown
    venues = Venue.query.order_by(Venue.name).all()
    
    # Get venue images if there's a venue assigned
    venue_images = []
    if tournament.venue_id:
        venue_images = VenueImage.query.filter_by(venue_id=tournament.venue_id).order_by(VenueImage.display_order).all()
    
    return render_template('organizer/edit_venue.html',
                          title='Edit Venue',
                          tournament=tournament,
                          venues=venues,
                          venue_images=venue_images,
                          form=form)
                          
@bp.route('/venues')
@login_required
@organizer_required # Or maybe admin_required depending on who manages venues globally
def venues():
    """List all venues"""
    venues = Venue.query.order_by(Venue.display_order, Venue.name).all()
    return render_template('organizer/edit_tournament/venues.html', # Consider moving templates to organizer/venue/
                          title='Manage Venues',
                          venues=venues)

@bp.route('/venue/create', methods=['GET', 'POST'])
@login_required
@organizer_required # Or admin_required
def create_venue():
    """Create a new venue"""
    form = VenueForm()
    if form.validate_on_submit():
        venue = Venue()
        form.populate_obj(venue) # Populate basic fields
        venue.display_order = form.display_order.data or 999 # Handle default

        if form.image.data: # Handle legacy image field upload
            venue.image = save_picture(form.image.data, 'venue_images')

        try:
            db.session.add(venue)
            db.session.commit()
            flash('Venue created successfully!', 'success')
            # Redirect to edit details to add gallery images
            return redirect(url_for('organizer.edit_venue_details', id=venue.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating venue: {e}', 'danger')

    return render_template('organizer/create_venue.html', # Consider moving templates
                          title='Create Venue',
                          form=form)

@bp.route('/venue/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@organizer_required # Or admin_required
def edit_venue_details(id):
    """Edit venue details and manage gallery"""
    venue = Venue.query.get_or_404(id)
    form = VenueForm(obj=venue)

    if form.validate_on_submit():
        form.populate_obj(venue) # Update fields
        venue.display_order = form.display_order.data or 999 # Handle default

        if form.image.data: # Handle legacy image field upload
            venue.image = save_picture(form.image.data, 'venue_images')

        try:
            db.session.commit()
            flash('Venue updated successfully!', 'success')
            return redirect(url_for('organizer.edit_tournament', id=id)) # Redirect back to list
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating venue: {e}', 'danger')

    # Get venue images for gallery section (already ordered by relationship)
    venue_images = venue.images.all()

    return render_template('organizer/edit_tournament/edit_venue_details.html', # Consider moving templates
                          title=f'Edit Venue: {venue.name}',
                          venue=venue,
                          venue_images=venue_images,
                          form=form)

@bp.route('/venue/<int:id>/add_image', methods=['GET', 'POST'])
@login_required
@organizer_required # Or admin_required
def add_venue_image(id):
    """Add an image to venue gallery"""
    venue = Venue.query.get_or_404(id)
    form = VenueImageForm()

    if form.validate_on_submit():
        try:
            # Save the new image
            image_path = save_picture(form.image.data, 'venue_images')
            if not image_path:
                 raise ValueError("Image could not be saved.")

            # If setting this as primary, unset all other primary images first
            if form.is_primary.data:
                VenueImage.query.filter_by(venue_id=id, is_primary=True).update({'is_primary': False})
                # Need to commit this change before adding the new primary
                # db.session.commit() # Or handle within the transaction

            # Get max display order + 1 if not specified
            display_order = form.display_order.data
            if display_order is None:
                max_order = db.session.query(db.func.max(VenueImage.display_order)).filter_by(venue_id=id).scalar() or 0
                display_order = max_order + 1

            venue_image = VenueImage(
                venue_id=id,
                image_path=image_path,
                caption=form.caption.data,
                is_primary=form.is_primary.data,
                display_order=display_order
            )
            db.session.add(venue_image)
            db.session.commit()
            flash('Image added to venue gallery.', 'success')
            return redirect(url_for('organizer.edit_venue_details', id=id))
        except Exception as e:
             db.session.rollback()
             flash(f'Error adding venue image: {e}', 'danger')


    return render_template('organizer/edit_tournament/add_venue_image.html', # Consider moving templates
                          title=f'Add Image to {venue.name}',
                          venue=venue,
                          form=form)

@bp.route('/venue/image/<int:image_id>/delete', methods=['POST'])
@login_required
@organizer_required # Or admin_required
def delete_venue_image(image_id):
    """Delete a venue image"""
    image = VenueImage.query.get_or_404(image_id)
    venue_id = image.venue_id # Store venue_id before deleting image object

    # Delete the file from storage
    if image.image_path:
        try:
            # Construct full path carefully
            image_full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], image.image_path.split('/')[-1]) # Adjust based on how save_picture stores paths
            if os.path.exists(image_full_path):
                os.remove(image_full_path)
            else:
                 current_app.logger.warning(f"Venue image file not found for deletion: {image_full_path}")
        except Exception as e:
            current_app.logger.error(f"Error deleting venue image file {image.image_path}: {e}")
            # Decide if you should still delete the DB record

    try:
        db.session.delete(image)
        db.session.commit()
        flash('Image deleted from gallery.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting image record: {e}', 'danger')

    return redirect(url_for('organizer.edit_venue_details', id=venue_id))

@bp.route('/venue/image/<int:image_id>/set_primary', methods=['POST'])
@login_required
@organizer_required # Or admin_required
def set_primary_venue_image(image_id):
    """Set a venue image as primary"""
    image_to_set = VenueImage.query.get_or_404(image_id)
    venue_id = image_to_set.venue_id

    try:
        # Unset other primary images for this venue in one query
        VenueImage.query.filter(
            VenueImage.venue_id == venue_id,
            VenueImage.id != image_id, # Don't unset the one we are setting
            VenueImage.is_primary == True
        ).update({'is_primary': False})

        # Set the selected image as primary
        image_to_set.is_primary = True
        db.session.commit()
        flash('Primary image updated.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error setting primary image: {e}', 'danger')

    return redirect(url_for('organizer.edit_venue_details', id=venue_id))

@bp.route('/venue/image/<int:image_id>/reorder', methods=['POST'])
@login_required
@organizer_required # Or admin_required
def reorder_venue_image(image_id):
    """Change the display order of a venue image"""
    image = VenueImage.query.get_or_404(image_id)
    venue_id = image.venue_id

    try:
        new_order = request.form.get('order', type=int)
        if new_order is not None and new_order > 0:
            image.display_order = new_order
            db.session.commit()
            flash('Image order updated.', 'success')
        else:
            flash('Invalid order value provided.', 'warning')
    except ValueError:
         flash('Invalid order value. Please enter a number.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating image order: {e}', 'danger')

    return redirect(url_for('organizer.edit_venue_details', id=venue_id))


# --- Tournament-Specific Venue Assignment ---

@bp.route('/tournament/<int:id>/venue', methods=['GET', 'POST'])
@login_required
@organizer_required
def edit_tournament_venue(id):
    """Assign or change the venue for a specific tournament"""
    tournament = Tournament.query.get_or_404(id)

    # Check permission
    if not current_user.is_admin() and tournament.organizer_id != current_user.id:
        flash('You do not have permission to edit this tournament venue.', 'danger')
        return redirect(url_for('organizer.tournament_detail', id=id))

    form = TournamentVenueForm()
    # Populate choices dynamically
    form.venue_id.choices = [(v.id, v.name) for v in Venue.query.order_by(Venue.name).all()]
    form.venue_id.choices.insert(0, (0, '-- Select Venue --')) # Add option for no venue

    if form.validate_on_submit():
        venue_id = form.venue_id.data
        if venue_id == 0: # Check for the '-- Select Venue --' option
             tournament.venue_id = None
             flash('Tournament venue unassigned.', 'success')
        else:
            venue = Venue.query.get(venue_id)
            if venue:
                tournament.venue_id = venue_id
                flash('Tournament venue updated successfully.', 'success')
            else:
                flash('Selected venue not found.', 'danger')
                # Don't change venue_id if selected venue is invalid
                return redirect(url_for('organizer.edit_tournament_venue', id=id))

        try:
            db.session.commit()
        except Exception as e:
             db.session.rollback()
             flash(f'Error updating tournament venue: {e}', 'danger')

        # Redirect back to the main tournament edit page or detail page
        return redirect(url_for('organizer.edit_tournament', id=id))

    # Pre-select current venue on GET request
    if request.method == 'GET':
        form.venue_id.data = tournament.venue_id if tournament.venue_id else 0

    # Get venue images if a venue is assigned (for display)
    venue_images = []
    if tournament.venue:
        venue_images = tournament.venue.images.all() # Assumes relationship is ordered

    return render_template('organizer/edit_tournament/edit_tournament_venue.html', # Consider moving templates
                          title='Assign Tournament Venue',
                          tournament=tournament,
                          venue_images=venue_images, # Pass images of current venue
                          form=form)