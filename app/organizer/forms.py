from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, IntegerField, FloatField, SelectField, DateField, TimeField, BooleanField, SubmitField, FieldList, FormField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, ValidationError
from datetime import datetime, timedelta
from app.models import TournamentTier, TournamentFormat, CategoryType, TournamentStatus

class TournamentForm(FlaskForm):
    name = StringField('Tournament Name', validators=[DataRequired(), Length(max=100)])
    location = StringField('Location', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[DataRequired()])
    start_date = DateField('Start Date', validators=[DataRequired()], format='%Y-%m-%d')
    end_date = DateField('End Date', validators=[DataRequired()], format='%Y-%m-%d')
    registration_deadline = DateField('Registration Deadline', validators=[DataRequired()], format='%Y-%m-%d')
    registration_fee = FloatField('Registration Fee ($)', validators=[DataRequired(), NumberRange(min=0)])
    tier = SelectField('Tournament Tier', validators=[DataRequired()], choices=[
        (TournamentTier.SLATE.name, 'SLATE (2,000 PTS)'),
        (TournamentTier.CUP.name, 'CUP (3,200 PTS)'), 
        (TournamentTier.OPEN.name, 'OPEN (1,400 PTS)'),
        (TournamentTier.CHALLENGE.name, 'CHALLENGE (925 PTS)')
    ])
    format = SelectField('Tournament Format', validators=[DataRequired()], choices=[
        (TournamentFormat.SINGLE_ELIMINATION.name, 'Single Elimination'),
        (TournamentFormat.DOUBLE_ELIMINATION.name, 'Double Elimination'),
        (TournamentFormat.ROUND_ROBIN.name, 'Round Robin'),
        (TournamentFormat.GROUP_KNOCKOUT.name, 'Group Stage + Knockout')
    ])
    prize_pool = FloatField('Prize Pool ($)', validators=[DataRequired(), NumberRange(min=0)])
    logo = FileField('Tournament Logo', validators=[
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])
    banner = FileField('Tournament Banner', validators=[
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])
    status = SelectField('Tournament Status', validators=[DataRequired()], choices=[
        (TournamentStatus.UPCOMING.name, 'Upcoming'),
        (TournamentStatus.ONGOING.name, 'Ongoing'),
        (TournamentStatus.COMPLETED.name, 'Completed')
    ])
    submit = SubmitField('Save Tournament')
    
    def validate_end_date(self, end_date):
        if end_date.data < self.start_date.data:
            raise ValidationError('End date must be after start date.')
    
    def validate_registration_deadline(self, registration_deadline):
        if registration_deadline.data > self.start_date.data:
            raise ValidationError('Registration deadline must be before the start date.')

class CategoryForm(FlaskForm):
    category_type = SelectField('Category', validators=[DataRequired()], choices=[
        (CategoryType.MENS_SINGLES.name, "Men's Singles"),
        (CategoryType.WOMENS_SINGLES.name, "Women's Singles"),
        (CategoryType.MENS_DOUBLES.name, "Men's Doubles"),
        (CategoryType.WOMENS_DOUBLES.name, "Women's Doubles"),
        (CategoryType.MIXED_DOUBLES.name, "Mixed Doubles")
    ])
    max_participants = IntegerField('Maximum Participants', validators=[DataRequired(), NumberRange(min=2, max=128)])
    points_awarded = IntegerField('Points Awarded', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Add Category')

class SeedingForm(FlaskForm):
    player_id = IntegerField('Player ID', validators=[DataRequired()])
    seed = IntegerField('Seed', validators=[NumberRange(min=1)])
    submit = SubmitField('Update Seed')

class MatchForm(FlaskForm):
    court = StringField('Court', validators=[Length(max=50)])
    scheduled_time = DateField('Date', format='%Y-%m-%d')
    scheduled_time_hour = TimeField('Time', format='%H:%M')
    player1_id = SelectField('Player 1', coerce=int)
    player2_id = SelectField('Player 2', coerce=int)
    player1_partner_id = SelectField('Player 1 Partner (doubles only)', coerce=int)
    player2_partner_id = SelectField('Player 2 Partner (doubles only)', coerce=int)
    submit = SubmitField('Save Match')

class ScoreForm(FlaskForm):
    set_number = IntegerField('Set', validators=[DataRequired(), NumberRange(min=1)])
    player1_score = IntegerField('Player 1 Score', validators=[DataRequired(), NumberRange(min=0)])
    player2_score = IntegerField('Player 2 Score', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Save Score')

class BracketGenerationForm(FlaskForm):
    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])
    use_seeding = BooleanField('Use Seeding')
    third_place_match = BooleanField('Include Third Place Match')
    submit = SubmitField('Generate Bracket')

class CompleteMatchForm(FlaskForm):
    match_id = IntegerField('Match ID', validators=[DataRequired()])
    winner_id = IntegerField('Winner ID', validators=[DataRequired()])
    completed = BooleanField('Mark as Completed')
    submit = SubmitField('Complete Match')
