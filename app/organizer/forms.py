from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, IntegerField, FloatField, SelectField, DateField, TimeField, BooleanField, SubmitField, FieldList, FormField, DecimalField
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


# class CategoryForm(FlaskForm):
#     category_type = SelectField('Category', validators=[DataRequired()], choices=[
#         (CategoryType.MENS_SINGLES.name, "Men's Singles"),
#         (CategoryType.WOMENS_SINGLES.name, "Women's Singles"),
#         (CategoryType.MENS_DOUBLES.name, "Men's Doubles"),
#         (CategoryType.WOMENS_DOUBLES.name, "Women's Doubles"),
#         (CategoryType.MIXED_DOUBLES.name, "Mixed Doubles")
#     ])
#     max_participants = IntegerField('Maximum Participants', validators=[DataRequired(), NumberRange(min=2, max=128)])
#     points_awarded = IntegerField('Points Awarded', validators=[DataRequired(), NumberRange(min=0)])
#     submit = SubmitField('Add Category')

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


class CategoryForm(FlaskForm):
    category_type = SelectField('Category Type', choices=[
        (CategoryType.MENS_SINGLES.name, 'Men\'s Singles'),
        (CategoryType.WOMENS_SINGLES.name, 'Women\'s Singles'),
        (CategoryType.MENS_DOUBLES.name, 'Men\'s Doubles'),
        (CategoryType.WOMENS_DOUBLES.name, 'Women\'s Doubles'),
        (CategoryType.MIXED_DOUBLES.name, 'Mixed Doubles'),
    ], validators=[DataRequired()])
    
    max_participants = IntegerField('Maximum Participants', 
                                  validators=[DataRequired(), NumberRange(min=2, message="Must have at least 2 participants")],
                                  default=32)
    
    points_awarded = IntegerField('Points Awarded', validators=[DataRequired()], default=100)
    
    registration_fee = DecimalField('Registration Fee', 
                                   validators=[Optional(), NumberRange(min=0)],
                                   default=0.0)
    
    # Format options
    format = SelectField('Category Format', choices=[
        (TournamentFormat.SINGLE_ELIMINATION.name, 'Single Elimination'),
        (TournamentFormat.DOUBLE_ELIMINATION.name, 'Double Elimination'),
        (TournamentFormat.ROUND_ROBIN.name, 'Round Robin'),
        (TournamentFormat.GROUP_KNOCKOUT.name, 'Group Stage + Knockout'),
    ], validators=[Optional()])
    
    # Prize money 
    prize_percentage = FloatField('Prize Percentage', 
                                validators=[Optional(), NumberRange(min=0, max=100)],
                                default=0)
    
    # DUPR rating restrictions
    min_dupr_rating = FloatField('Minimum DUPR Rating', 
                              validators=[Optional(), NumberRange(min=0, max=8.0)])
    max_dupr_rating = FloatField('Maximum DUPR Rating', 
                              validators=[Optional(), NumberRange(min=0, max=8.0)])
    
    # Age restrictions
    min_age = IntegerField('Minimum Age', 
                         validators=[Optional(), NumberRange(min=0, max=120)])
    max_age = IntegerField('Maximum Age', 
                         validators=[Optional(), NumberRange(min=0, max=120)])
    
    # Gender restriction
    gender_restriction = SelectField('Gender Restriction', choices=[
        ('', 'No Restriction'),
        ('male', 'Male Only'),
        ('female', 'Female Only'),
        ('mixed', 'Mixed')
    ], validators=[Optional()])
    
    # Format-specific settings
    group_count = IntegerField('Number of Groups', 
                             validators=[Optional(), NumberRange(min=0)],
                             default=0)
    teams_per_group = IntegerField('Teams Per Group', 
                                 validators=[Optional(), NumberRange(min=0)],
                                 default=0)
    teams_advancing_per_group = IntegerField('Teams Advancing Per Group', 
                                           validators=[Optional(), NumberRange(min=0)],
                                           default=0)


class TournamentGiftsForm(FlaskForm):
    door_gifts = TextAreaField('Door Gifts Description', 
                             validators=[Optional(), Length(max=1000)],
                             description="Describe the door gifts participants will receive")
    
    door_gifts_image = FileField('Door Gifts Image', 
                               validators=[Optional(), 
                                         FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])

class TournamentPaymentForm(FlaskForm):
    payment_bank_name = StringField('Bank Name', 
                                  validators=[DataRequired(), Length(max=100)])
    
    payment_account_number = StringField('Account Number', 
                                      validators=[DataRequired(), Length(max=50)])
    
    payment_account_name = StringField('Account Name', 
                                     validators=[DataRequired(), Length(max=100)])
    
    payment_reference_prefix = StringField('Payment Reference Prefix', 
                                         validators=[Optional(), Length(max=20)],
                                         description="Prefix for payment references (e.g., 'PBT' will generate references like 'PBT-123456789')")
    
    payment_qr_code = FileField('Payment QR Code', 
                              validators=[Optional(), 
                                        FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])
    
    payment_instructions = TextAreaField('Payment Instructions', 
                                       validators=[Optional(), Length(max=1000)],
                                       description="Additional payment instructions for players")



