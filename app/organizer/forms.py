from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, IntegerField, FloatField, SelectField, DateField, DateTimeField, TimeField, BooleanField, SubmitField, FieldList, FormField, DecimalField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, ValidationError
from datetime import datetime, timedelta
from app.models import TournamentTier, TournamentFormat, CategoryType, TournamentStatus, Venue, SponsorTier


class TournamentForm(FlaskForm):
    name = StringField('Tournament Name', validators=[DataRequired(), Length(min=5, max=100)])
    location = StringField('Location', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[DataRequired()])
    
    start_date = DateTimeField('Start Date', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    end_date = DateTimeField('End Date', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    registration_deadline = DateTimeField('Registration Deadline', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    
    tier = SelectField('Tournament Tier', 
                      choices=[(tier.name, tier.value) for tier in TournamentTier], 
                      validators=[DataRequired()])
    
    format = SelectField('Tournament Format', 
                        choices=[(fmt.name, fmt.value) for fmt in TournamentFormat], 
                        validators=[DataRequired()])
    
    status = SelectField('Tournament Status', 
                        choices=[(status.name, status.value) for status in TournamentStatus], 
                        validators=[DataRequired()])
    
    prize_pool = FloatField('Prize Pool (RM)', validators=[Optional(), NumberRange(min=0)])
    
    # Upload fields
    logo = FileField('Tournament Logo', validators=[
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])
    banner = FileField('Tournament Banner', validators=[
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])
    
    # Payment details
    payment_bank_name = StringField('Bank Name', validators=[Optional(), Length(max=100)])
    payment_account_number = StringField('Account Number', validators=[Optional(), Length(max=50)])
    payment_account_name = StringField('Account Name', validators=[Optional(), Length(max=100)])
    payment_reference_prefix = StringField('Payment Reference Prefix', validators=[Optional(), Length(max=20)])
    payment_qr_code = FileField('Payment QR Code', validators=[
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])
    payment_instructions = TextAreaField('Payment Instructions', validators=[Optional()])
    
    # Door gifts
    door_gifts = TextAreaField('Door Gifts', validators=[Optional()])
    door_gifts_image = FileField('Door Gifts Image', validators=[
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])
    
    # Prize details
    prize_structure_description = TextAreaField('Prize Structure Description', validators=[Optional()])
    
    # Venue selection (would need to be populated with choices)
    venue_id = SelectField('Venue', coerce=int, validators=[Optional()])

    submit = SubmitField('Save Tournament Details')
    
    def validate_end_date(self, end_date):
        if end_date.data < self.start_date.data:
            raise ValidationError('End date must be after start date.')
    
    def validate_registration_deadline(self, registration_deadline):
        if registration_deadline.data > self.start_date.data:
            raise ValidationError('Registration deadline must be before the start date.')

    def __init__(self, *args, **kwargs):
        super(TournamentForm, self).__init__(*args, **kwargs)
        # Now populate choices here, when the form is instantiated
   
        venues = Venue.query.order_by(Venue.name).all()
        self.venue_id.choices = [(0, 'Select Venue')] + [
            (venue.id, venue.name) for venue in venues
        ]

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



class VenueForm(FlaskForm):
    name = StringField('Venue Name', validators=[DataRequired(), Length(min=3, max=100)])
    address = StringField('Address', validators=[DataRequired(), Length(max=255)])
    city = StringField('City', validators=[DataRequired(), Length(max=100)])
    state = StringField('State/Province', validators=[DataRequired(), Length(max=100)])
    country = StringField('Country', validators=[DataRequired(), Length(max=100)])
    postal_code = StringField('Postal Code', validators=[Optional(), Length(max=20)])
    
    description = TextAreaField('Description', validators=[Optional(), Length(max=2000)])
    website = StringField('Website', validators=[Optional(), Length(max=255)])
    court_count = IntegerField('Number of Courts', validators=[Optional(), NumberRange(min=0)])
    
    is_featured = BooleanField('Feature this Venue')
    display_order = IntegerField('Display Order', validators=[Optional(), NumberRange(min=1)])
    
    contact_email = StringField('Contact Email', validators=[Optional(), Length(max=100)])
    contact_phone = StringField('Contact Phone', validators=[Optional(), Length(max=50)])
    facilities = TextAreaField('Facilities', validators=[Optional(), Length(max=1000)])
    amenities = TextAreaField('Amenities', validators=[Optional(), Length(max=1000)])
    parking_info = TextAreaField('Parking Information', validators=[Optional(), Length(max=1000)])
    google_maps_url = StringField('Google Maps URL', validators=[Optional(), Length(max=255)])
    
    image = FileField('Main Venue Image', validators=[
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])
    
    submit = SubmitField('Save Venue')


class VenueImageForm(FlaskForm):
    image = FileField('Venue Image', validators=[
        DataRequired(),
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])
    caption = StringField('Caption', validators=[Optional(), Length(max=255)])
    is_primary = BooleanField('Set as Primary Image')
    display_order = IntegerField('Display Order', validators=[Optional(), NumberRange(min=1)])
    
    submit = SubmitField('Add Image')


class SponsorForm(FlaskForm):
    name = StringField('Sponsor Name', validators=[DataRequired(), Length(min=3, max=100)])
    tier = SelectField('Sponsor Tier', choices=[
        (tier.name, tier.value) for tier in SponsorTier
    ], validators=[DataRequired()])
    
    description = TextAreaField('Description', validators=[Optional(), Length(max=2000)])
    website = StringField('Website', validators=[Optional(), Length(max=255)])
    is_featured = BooleanField('Feature this Sponsor')
    display_order = IntegerField('Display Order', validators=[Optional(), NumberRange(min=1)])
    
    contact_name = StringField('Contact Name', validators=[Optional(), Length(max=100)])
    contact_email = StringField('Contact Email', validators=[Optional(), Length(max=100)])
    contact_phone = StringField('Contact Phone', validators=[Optional(), Length(max=50)])
    
    logo = FileField('Sponsor Logo', validators=[
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])
    banner_image = FileField('Banner Image', validators=[
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])
    
    submit = SubmitField('Save Sponsor')


class TournamentSponsorForm(FlaskForm):
    sponsors = FieldList(IntegerField('Sponsor ID'))
    sponsor_order = FieldList(IntegerField('Order'))
    
    submit = SubmitField('Save Sponsors')


class TournamentVenueForm(FlaskForm):
    venue_id = IntegerField('Venue ID', validators=[Optional()])
    
    submit = SubmitField('Save Venue')