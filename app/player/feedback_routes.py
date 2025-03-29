from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import current_user, login_required
from datetime import datetime

from app import db
from app.player import bp
from app.models import Feedback, Tournament, User, UserRole
from app.decorators import player_required
from app.player.feedback_forms import FeedbackForm

@bp.route('/submit_feedback/tournament/<int:tournament_id>', methods=['GET', 'POST'])
@login_required
@player_required
def submit_tournament_feedback(tournament_id):
    """Submit feedback for a tournament"""
    tournament = Tournament.query.get_or_404(tournament_id)
    
    # Check if user has already submitted feedback for this tournament
    existing_feedback = Feedback.query.filter_by(
        user_id=current_user.id,
        tournament_id=tournament_id
    ).first()
    
    if existing_feedback:
        flash('You have already submitted feedback for this tournament. You can edit your existing feedback instead.', 'info')
        return redirect(url_for('player.edit_feedback', feedback_id=existing_feedback.id))
    
    form = FeedbackForm()
    form.tournament_id.data = tournament_id
    
    if form.validate_on_submit():
        feedback = Feedback(
            user_id=current_user.id,
            tournament_id=tournament_id,
            rating=form.rating.data,
            comment=form.comment.data,
            is_anonymous=form.is_anonymous.data,
            created_at=datetime.utcnow()
        )
        
        try:
            db.session.add(feedback)
            db.session.commit()
            flash('Your feedback has been submitted. Thank you!', 'success')
            return redirect(url_for('main.tournament_detail', id=tournament_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error submitting feedback: {e}', 'danger')
    
    return render_template('player/submit_feedback.html',
                          title=f'Feedback for {tournament.name}',
                          form=form,
                          tournament=tournament)

@bp.route('/submit_feedback/organizer/<int:organizer_id>', methods=['GET', 'POST'])
@login_required
@player_required
def submit_organizer_feedback(organizer_id):
    """Submit feedback for a tournament organizer"""
    organizer = User.query.filter_by(id=organizer_id, role=UserRole.ORGANIZER).first_or_404()
    
    # Check if user has already submitted feedback for this organizer
    existing_feedback = Feedback.query.filter_by(
        user_id=current_user.id,
        organizer_id=organizer_id
    ).first()
    
    if existing_feedback:
        flash('You have already submitted feedback for this organizer. You can edit your existing feedback instead.', 'info')
        return redirect(url_for('player.edit_feedback', feedback_id=existing_feedback.id))
    
    form = FeedbackForm()
    form.organizer_id.data = organizer_id
    
    if form.validate_on_submit():
        feedback = Feedback(
            user_id=current_user.id,
            organizer_id=organizer_id,
            rating=form.rating.data,
            comment=form.comment.data,
            is_anonymous=form.is_anonymous.data,
            created_at=datetime.utcnow()
        )
        
        try:
            db.session.add(feedback)
            db.session.commit()
            flash('Your feedback has been submitted. Thank you!', 'success')
            return redirect(url_for('main.organizer_detail', id=organizer_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error submitting feedback: {e}', 'danger')
    
    return render_template('player/submit_feedback.html',
                          title=f'Feedback for {organizer.full_name}',
                          form=form,
                          organizer=organizer)

@bp.route('/edit_feedback/<int:feedback_id>', methods=['GET', 'POST'])
@login_required
@player_required
def edit_feedback(feedback_id):
    """Edit previously submitted feedback"""
    feedback = Feedback.query.get_or_404(feedback_id)
    
    # Ensure the current user is the owner of this feedback
    if feedback.user_id != current_user.id:
        abort(403)  # Forbidden
    
    form = FeedbackForm(obj=feedback)
    
    if request.method == 'GET':
        # Pre-fill the form
        if feedback.tournament_id:
            form.tournament_id.data = feedback.tournament_id
        elif feedback.organizer_id:
            form.organizer_id.data = feedback.organizer_id
    
    if form.validate_on_submit():
        feedback.rating = form.rating.data
        feedback.comment = form.comment.data
        feedback.is_anonymous = form.is_anonymous.data
        feedback.updated_at = datetime.utcnow()
        
        try:
            db.session.commit()
            flash('Your feedback has been updated.', 'success')
            
            if feedback.tournament_id:
                return redirect(url_for('main.tournament_detail', id=feedback.tournament_id))
            else:
                return redirect(url_for('main.organizer_detail', id=feedback.organizer_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating feedback: {e}', 'danger')
    
    return render_template('player/edit_feedback.html',
                          title='Edit Feedback',
                          form=form,
                          feedback=feedback)

@bp.route('/my_feedback')
@login_required
@player_required
def my_feedback():
    """View all feedback submitted by the current user"""
    feedback_list = Feedback.query.filter_by(user_id=current_user.id).order_by(Feedback.created_at.desc()).all()
    
    return render_template('player/my_feedback.html',
                          title='My Feedback',
                          feedback_list=feedback_list)