from flask import current_app, render_template
from flask_mail import Message
from app import mail
from app.models import Match, Registration, User, Tournament
from datetime import datetime, timedelta

def send_match_reminder_email(match_id, is_day_before=False):
    """
    Send a reminder email to players about their upcoming match.
    
    Args:
        match_id: The ID of the match to send reminders for
        is_day_before: True if this is a 24-hour reminder, False for a 1-hour reminder
    """
    with current_app.app_context():
        match = Match.query.get(match_id)
        if not match or not match.scheduled_time:
            current_app.logger.error(f"Cannot send reminder for match {match_id}: Match not found or no scheduled time")
            return
        
        # Skip if the match is already completed or scheduled time is in the past
        if match.completed or match.scheduled_time < datetime.now():
            return
            
        # Get the players involved in the match
        players = []
        
        # For singles matches
        if not match.is_doubles:
            if match.player1_id:
                user = User.query.join(User.player_profile).filter(
                    User.player_profile.has(id=match.player1_id)
                ).first()
                if user:
                    players.append(user)
                    
            if match.player2_id:
                user = User.query.join(User.player_profile).filter(
                    User.player_profile.has(id=match.player2_id)
                ).first()
                if user:
                    players.append(user)
        
        # For doubles matches
        else:
            if match.team1_id:
                team = match.team1_profile
                if team:
                    for player_id in [team.player1_id, team.player2_id]:
                        user = User.query.join(User.player_profile).filter(
                            User.player_profile.has(id=player_id)
                        ).first()
                        if user:
                            players.append(user)
            
            if match.team2_id:
                team = match.team2_profile
                if team:
                    for player_id in [team.player1_id, team.player2_id]:
                        user = User.query.join(User.player_profile).filter(
                            User.player_profile.has(id=player_id)
                        ).first()
                        if user:
                            players.append(user)
        
        if not players:
            current_app.logger.error(f"No players found for match {match_id}")
            return
            
        # Get tournament information
        tournament = match.category.tournament
        category_name = match.category.category_type.value
        
        # Determine reminder time frame for subject line
        time_frame = "24 hours" if is_day_before else "soon"
        
        # Prepare and send email to each player
        for player in players:
            if not player.email:
                continue
                
            msg = Message(
                subject=f"Reminder: Your match in {tournament.name} starts in {time_frame}",
                recipients=[player.email]
            )
            
            msg.body = render_template(
                'email/match_reminder.txt',
                user=player,
                match=match,
                tournament=tournament,
                category_name=category_name,
                is_day_before=is_day_before
            )
            
            msg.html = render_template(
                'email/match_reminder.html',
                user=player,
                match=match,
                tournament=tournament,
                category_name=category_name,
                is_day_before=is_day_before
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
        changes: Dictionary of changed attributes (e.g. {'court': 'Court 3', 'scheduled_time': datetime object})
    """
    with current_app.app_context():
        match = Match.query.get(match_id)
        if not match:
            current_app.logger.error(f"Cannot send schedule change for match {match_id}: Match not found")
            return
            
        # Get the players involved in the match
        players = []
        
        # For singles matches
        if not match.is_doubles:
            if match.player1_id:
                user = User.query.join(User.player_profile).filter(
                    User.player_profile.has(id=match.player1_id)
                ).first()
                if user:
                    players.append(user)
                    
            if match.player2_id:
                user = User.query.join(User.player_profile).filter(
                    User.player_profile.has(id=match.player2_id)
                ).first()
                if user:
                    players.append(user)
        
        # For doubles matches
        else:
            if match.team1_id:
                team = match.team1_profile
                if team:
                    for player_id in [team.player1_id, team.player2_id]:
                        user = User.query.join(User.player_profile).filter(
                            User.player_profile.has(id=player_id)
                        ).first()
                        if user:
                            players.append(user)
            
            if match.team2_id:
                team = match.team2_profile
                if team:
                    for player_id in [team.player1_id, team.player2_id]:
                        user = User.query.join(User.player_profile).filter(
                            User.player_profile.has(id=player_id)
                        ).first()
                        if user:
                            players.append(user)
        
        if not players:
            current_app.logger.error(f"No players found for match {match_id}")
            return
            
        # Format changes for display
        formatted_changes = {}
        if 'court' in changes:
            formatted_changes['Court'] = changes['court']
        if 'scheduled_time' in changes:
            # Convert string time to datetime object if needed
            if isinstance(changes['scheduled_time'], str):
                try:
                    formatted_time = datetime.strptime(changes['scheduled_time'], '%Y-%m-%d %H:%M')
                    formatted_changes['Time'] = formatted_time.strftime('%I:%M %p, %d %B %Y')
                except ValueError:
                    formatted_changes['Time'] = changes['scheduled_time']
            else:
                formatted_changes['Time'] = changes['scheduled_time'].strftime('%I:%M %p, %d %B %Y') if changes['scheduled_time'] else 'TBD'
        if 'livestream_url' in changes:
            formatted_changes['Livestream'] = changes['livestream_url'] or 'Removed'
            
        # Get tournament information
        tournament = match.category.tournament
        category_name = match.category.category_type.value
        
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
                changes=formatted_changes
            )
            
            msg.html = render_template(
                'email/schedule_change.html',
                user=player,
                match=match,
                tournament=tournament,
                category_name=category_name,
                changes=formatted_changes
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
