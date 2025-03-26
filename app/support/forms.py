from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, HiddenField, SubmitField
from wtforms.validators import DataRequired, Length, Optional
from app.models import TicketType

class SupportTicketForm(FlaskForm):
    tournament_id = HiddenField('Tournament ID')
    ticket_type = SelectField('Ticket Type', 
                             choices=[(t.name, t.value) for t in TicketType],
                             validators=[DataRequired()])
    subject = StringField('Subject', validators=[DataRequired(), Length(min=5, max=200)])
    description = TextAreaField('Description', validators=[DataRequired(), Length(min=10, max=5000)])
    reported_player_id = HiddenField('Reported Player ID')
    submit = SubmitField('Submit Ticket')

class TicketResponseForm(FlaskForm):
    message = TextAreaField('Response', validators=[DataRequired(), Length(min=1, max=5000)])
    submit = SubmitField('Send Response')

class UpdateTicketStatusForm(FlaskForm):
    status = SelectField('Status', choices=[
        ('OPEN', 'Open'),
        ('IN_PROGRESS', 'In Progress'),
        ('RESOLVED', 'Resolved'),
        ('CLOSED', 'Closed')
    ])
    submit = SubmitField('Update Status')