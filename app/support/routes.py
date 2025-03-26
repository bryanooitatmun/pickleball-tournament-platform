# Create a new file app/support/routes.py

from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import current_user, login_required
from app import db
from app.support import bp
from app.support.forms import SupportTicketForm, TicketResponseForm, UpdateTicketStatusForm
from app.models import Tournament, SupportTicket, TicketResponse, TicketStatus, TicketType, PlayerProfile
from datetime import datetime

@bp.route('/create/<int:tournament_id>', methods=['GET', 'POST'])
@login_required
def create_ticket(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)
    form = SupportTicketForm()
    form.tournament_id.data = tournament_id
    
    # Check if this is a player report
    reported_player_id = request.args.get('report_player', type=int)
    if reported_player_id:
        reported_player = PlayerProfile.query.get_or_404(reported_player_id)
        form.ticket_type.data = TicketType.PLAYER_REPORT.name
        form.reported_player_id.data = reported_player_id
        form.subject.data = f"Player Report: {reported_player.full_name}"
    
    if form.validate_on_submit():
        # Create new ticket
        ticket = SupportTicket(
            tournament_id=tournament_id,
            submitter_id=current_user.id,
            ticket_type=TicketType[form.ticket_type.data],
            subject=form.subject.data,
            description=form.description.data,
            status=TicketStatus.OPEN
        )
        
        # Set reported player if this is a player report
        if form.reported_player_id.data:
            ticket.reported_player_id = form.reported_player_id.data
        
        db.session.add(ticket)
        db.session.commit()
        
        flash('Your support ticket has been submitted. The tournament organizer will review it shortly.', 'success')
        return redirect(url_for('main.tournament_detail', id=tournament_id))
    
    return render_template('support/create_ticket.html',
                          title='Create Support Ticket',
                          tournament=tournament,
                          form=form,
                          reported_player=PlayerProfile.query.get(reported_player_id) if reported_player_id else None)

@bp.route('/my-tickets')
@login_required
def my_tickets():
    tickets = SupportTicket.query.filter_by(submitter_id=current_user.id).order_by(SupportTicket.updated_at.desc()).all()
    return render_template('support/my_tickets.html',
                          title='My Support Tickets',
                          tickets=tickets)

@bp.route('/ticket/<int:ticket_id>', methods=['GET', 'POST'])
@login_required
def view_ticket(ticket_id):
    ticket = SupportTicket.query.get_or_404(ticket_id)
    
    # Only the ticket submitter, tournament organizer, or admin can view the ticket
    if (ticket.submitter_id != current_user.id and 
        ticket.tournament.organizer_id != current_user.id and 
        not current_user.is_admin()):
        abort(403)
    
    response_form = TicketResponseForm()
    status_form = UpdateTicketStatusForm()
    
    # Pre-fill status form
    status_form.status.data = ticket.status.name
    
    if response_form.validate_on_submit():
        # Add new response
        response = TicketResponse(
            ticket_id=ticket.id,
            user_id=current_user.id,
            message=response_form.message.data
        )
        db.session.add(response)
        
        # Update ticket's last updated time
        ticket.updated_at = datetime.utcnow()
        
        # If organizer responds, set status to in progress if currently open
        if (current_user.id == ticket.tournament.organizer_id or current_user.is_admin()) and ticket.status == TicketStatus.OPEN:
            ticket.status = TicketStatus.IN_PROGRESS
        
        db.session.commit()
        
        flash('Your response has been added.', 'success')
        return redirect(url_for('support.view_ticket', ticket_id=ticket.id))
    
    # Load responses with users
    responses = ticket.responses.order_by(TicketResponse.created_at).all()
    
    return render_template('support/view_ticket.html',
                          title=f'Ticket: {ticket.subject}',
                          ticket=ticket,
                          responses=responses,
                          response_form=response_form,
                          status_form=status_form,
                          is_organizer=(current_user.id == ticket.tournament.organizer_id or current_user.is_admin()))

@bp.route('/ticket/<int:ticket_id>/status', methods=['POST'])
@login_required
def update_ticket_status(ticket_id):
    ticket = SupportTicket.query.get_or_404(ticket_id)
    
    # Only the tournament organizer or admin can update status
    if ticket.tournament.organizer_id != current_user.id and not current_user.is_admin():
        abort(403)
    
    form = UpdateTicketStatusForm()
    
    if form.validate_on_submit():
        ticket.status = TicketStatus[form.status.data]
        ticket.updated_at = datetime.utcnow()
        
        # Add system message about status change
        message = f"Ticket status changed to: {ticket.status.value}"
        response = TicketResponse(
            ticket_id=ticket.id,
            user_id=current_user.id,
            message=message
        )
        db.session.add(response)
        db.session.commit()
        
        flash(f'Ticket status updated to {ticket.status.value}', 'success')
    
    return redirect(url_for('support.view_ticket', ticket_id=ticket.id))

# Organizer ticket management routes
@bp.route('/tournament/<int:tournament_id>/tickets')
@login_required
def tournament_tickets(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)
    
    # Check if user is the organizer or admin
    if tournament.organizer_id != current_user.id and not current_user.is_admin():
        abort(403)
    
    # Get tickets filtered by status
    status_filter = request.args.get('status', 'all')
    
    if status_filter != 'all':
        try:
            status = TicketStatus[status_filter.upper()]
            tickets = SupportTicket.query.filter_by(
                tournament_id=tournament_id,
                status=status
            ).order_by(SupportTicket.updated_at.desc()).all()
        except KeyError:
            tickets = SupportTicket.query.filter_by(tournament_id=tournament_id).order_by(SupportTicket.updated_at.desc()).all()
    else:
        tickets = SupportTicket.query.filter_by(tournament_id=tournament_id).order_by(SupportTicket.updated_at.desc()).all()
    
    # Count by status
    status_counts = {}
    for status in TicketStatus:
        count = SupportTicket.query.filter_by(tournament_id=tournament_id, status=status).count()
        status_counts[status.name] = count
    
    return render_template('support/tournament_tickets.html',
                          title=f'{tournament.name} - Support Tickets',
                          tournament=tournament,
                          tickets=tickets,
                          status_filter=status_filter,
                          status_counts=status_counts)