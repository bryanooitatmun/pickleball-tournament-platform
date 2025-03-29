from flask import current_app, render_template
from flask_mail import Message
from app import mail
from app.models import Match, Registration, User, Tournament
from datetime import datetime, timedelta

def send_match_reminder_email(match_id):
    """
    Send a reminder email to players about their upcoming match.
    
    Args:
        match_id: The ID of the match to send reminders for
    """
    with current_app.app_context():
        match = Match.query.get(match_id)
        if not match or not match.scheduled_time:
            current_app.logger.error(f"Cannot send reminder for match {match_id}: Match not found or no scheduled time")
            return
        
        # Skip if the match is not scheduled or already completed
        if match.status != 'scheduled' or match.scheduled_time < datetime.now():
            return
            
        # Get the players involved in the match
        players = []
        for team in match.teams:
            for registration in team.registrations:
                players.append(registration.user)
        
        if not players:
            current_app.logger.error(f"No players found for match {match_id}")
            return
            
        # Get tournament information
        tournament = match.category.tournament
        category_name = match.category.name
        
        # Prepare and send email to each player
        for player in players:
            if not player.email:
                continue
                
            msg = Message(
                subject=f"Reminder: Your match in {tournament.name} starts soon",
                recipients=[player.email]
            )
            
            msg.body = render_template(
                'email/match_reminder.txt',
                user=player,
                match=match,
                tournament=tournament,
                category_name=category_name
            )
            
            msg.html = render_template(
                'email/match_reminder.html',
                user=player,
                match=match,
                tournament=tournament,
                category_name=category_name
            )
            
            try:
                mail.send(msg)
                current_app.logger.info(f"Sent match reminder to {player.email} for match {match_id}")
            except Exception as e:
                current_app.logger.error(f"Failed to send match reminder to {player.email}: {str(e)}")


def send_schedule_change_email(match_id, changes):
    """
    Send notification email about schedule or court changes.
    
    Args:
        match_id: The ID of the match that was changed
        changes: Dictionary of changed attributes (e.g. {'court': 'Court 3', 'scheduled_time': '2023-10-01 15:00'})
    """
    with current_app.app_context():
        match = Match.query.get(match_id)
        if not match:
            current_app.logger.error(f"Cannot send schedule change for match {match_id}: Match not found")
            return
            
        # Get the players involved in the match
        players = []
        for team in match.teams:
            for registration in team.registrations:
                players.append(registration.user)
        
        if not players:
            current_app.logger.error(f"No players found for match {match_id}")
            return
            
        # Get tournament information
        tournament = match.category.tournament
        category_name = match.category.name
        
        # Prepare and send email to each player
        for player in players:
            if not player.email:
                continue
                
            msg = Message(
                subject=f"Schedule Change: Your match in {tournament.name}",
                recipients=[player.email]
            )
            
            msg.body = render_template(
                'email/schedule_change.txt',
                user=player,
                match=match,
                tournament=tournament,
                category_name=category_name,
                changes=changes
            )
            
            msg.html = render_template(
                'email/schedule_change.html',
                user=player,
                match=match,
                tournament=tournament,
                category_name=category_name,
                changes=changes
            )
            
            try:
                mail.send(msg)
                current_app.logger.info(f"Sent schedule change notification to {player.email} for match {match_id}")
            except Exception as e:
                current_app.logger.error(f"Failed to send schedule change notification to {player.email}: {str(e)}")
                

def send_announcement_email(tournament_id, subject, message, recipients=None):
    """
    Send a general announcement email to tournament participants.
    
    Args:
        tournament_id: The ID of the tournament
        subject: Email subject
        message: Email message content
        recipients: Optional list of user IDs to send to (if None, sends to all tournament participants)
    """
    with current_app.app_context():
        tournament = Tournament.query.get(tournament_id)
        if not tournament:
            current_app.logger.error(f"Cannot send announcement for tournament {tournament_id}: Tournament not found")
            return
            
        # Get all participants if no specific recipients list
        users = []
        if recipients:
            users = User.query.filter(User.id.in_(recipients)).all()
        else:
            # Get all players registered for this tournament
            registrations = Registration.query.join(
                Registration.category
            ).filter(
                Registration.status == 'approved',
                Registration.category.has(tournament_id=tournament_id)
            ).all()
            
            user_ids = set()
            for registration in registrations:
                user_ids.add(registration.user_id)
                
            users = User.query.filter(User.id.in_(user_ids)).all()
            
        if not users:
            current_app.logger.error(f"No recipients found for announcement for tournament {tournament_id}")
            return
            
        # Prepare and send email to each user
        for user in users:
            if not user.email:
                continue
                
            msg = Message(
                subject=f"{tournament.name}: {subject}",
                recipients=[user.email]
            )
            
            msg.body = render_template(
                'email/announcement.txt',
                user=user,
                tournament=tournament,
                message=message
            )
            
            msg.html = render_template(
                'email/announcement.html',
                user=user,
                tournament=tournament,
                message=message
            )
            
            try:
                mail.send(msg)
                current_app.logger.info(f"Sent announcement to {user.email} for tournament {tournament_id}")
            except Exception as e:
                current_app.logger.error(f"Failed to send announcement to {user.email}: {str(e)}")
