from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, IntegerField, FloatField, SelectField, DateField, DateTimeField, TimeField, BooleanField, SubmitField, FieldList, FormField, DecimalField, HiddenField, URLField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, ValidationError, URL
from datetime import datetime, timedelta
from app.models import TournamentTier, TournamentFormat, CategoryType, TournamentStatus, Venue, SponsorTier

def validate_file_size(max_size_mb=5):
    """
    Creates a validator that checks if the file size is within the specified limit.
    
    Args:
        max_size_mb (float): Maximum file size in megabytes
        
    Returns:
        function: A validator function that can be used with WTForms
    """
    def _validate_file_size(form, field):
        if isinstance(field.data, str):
            return True
        if field.data:
            # Get file size in bytes and convert to MB
            file_size = len(field.data.read()) / 1024 / 1024
            field.data.seek(0)  # Reset file pointer after reading
            
            if file_size > max_size_mb:
                raise ValidationError(f'File size too large. Maximum allowed size is {max_size_mb}MB. Your file is {file_size:.1f}MB.')
    
    return _validate_file_size

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
    
    is_ranked = BooleanField('Ranked Tournament (contributes to player rankings)', default=True)

    format = SelectField('Tournament Format', 
                        choices=[(fmt.name, fmt.value) for fmt in TournamentFormat], 
                        validators=[DataRequired()])
    
    status = SelectField('Tournament Status', 
                        choices=[(status.name, status.value) for status in TournamentStatus], 
                        validators=[DataRequired()])
    
    prize_pool = FloatField('Prize Pool (RM)', validators=[NumberRange(min=0)])
    
    # Upload fields
    logo = FileField('Tournament Logo', validators=[
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!'),
        validate_file_size(max_size_mb=5)
    ])
    banner = FileField('Tournament Banner', validators=[
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!'),
        validate_file_size(max_size_mb=5)
    ])
    
    # Payment details
    payment_bank_name = StringField('Bank Name', validators=[Optional(), Length(max=100)])
    payment_account_number = StringField('Account Number', validators=[Optional(), Length(max=50)])
    payment_account_name = StringField('Account Name', validators=[Optional(), Length(max=100)])
    payment_reference_prefix = StringField('Payment Reference Prefix', validators=[Optional(), Length(max=20)])
    payment_qr_code = FileField('Payment QR Code', validators=[
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!'),
        validate_file_size(max_size_mb=5)
    ])
    payment_instructions = TextAreaField('Payment Instructions', validators=[Optional()])
    
    # Door gifts
    door_gifts = TextAreaField('Door Gifts', validators=[Optional()])
    door_gifts_image = FileField('Door Gifts Image', validators=[
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!'),
        validate_file_size(max_size_mb=5)
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

class SeedingForm(FlaskForm):
    player_id = IntegerField('Player ID', validators=[DataRequired()])
    seed = IntegerField('Seed', validators=[NumberRange(min=1)])
    submit = SubmitField('Update Seed')

class ScoreForm(FlaskForm):
    """Form for a single set score entry"""
    player1_score = IntegerField('Player/Team 1 Score', validators=[NumberRange(min=0)], default=0)
    player2_score = IntegerField('Player/Team 2 Score', validators=[NumberRange(min=0)], default=0)

class MatchForm(FlaskForm):
    """Form for editing match details"""
    court = StringField('Court Assignment', validators=[Optional(), Length(max=50)])
    scheduled_time = DateTimeField('Scheduled Time', format='%Y-%m-%dT%H:%M', validators=[Optional()])
    livestream_url = URLField('Livestream URL', validators=[Optional(), URL()])  # Will fail on invalid URLs
    
    # Score information
    set_count = IntegerField('Number of Sets', validators=[NumberRange(min=0, max=5)], default=0)
    scores = FieldList(FormField(ScoreForm), min_entries=0, max_entries=5)
    
    # Verification flags
    referee_verified = BooleanField('Referee Verified', default=False)
    player_verified = BooleanField('Player Verified', default=False)
    
    def __init__(self, *args, **kwargs):
        super(MatchForm, self).__init__(*args, **kwargs)
        # Pre-populate with 3 score forms by default
        while len(self.scores) < 3:
            self.scores.append_entry()

class CompleteMatchForm(FlaskForm):
    """Form for completing a match with scores and winner"""
    # Hidden fields for match identification
    match_id = HiddenField('Match ID', validators=[DataRequired()])
    
    # Score information
    set_count = IntegerField('Number of Sets', validators=[NumberRange(min=1, max=5)], default=3)
    scores = FieldList(FormField(ScoreForm), min_entries=1, max_entries=5)
    
    # Verification
    referee_verified = BooleanField('I verify that these scores are correct', default=False)
    
    def __init__(self, *args, **kwargs):
        super(CompleteMatchForm, self).__init__(*args, **kwargs)
        # Pre-populate with 3 score forms by default
        while len(self.scores) < 3:
            self.scores.append_entry()

class BulkMatchForm(FlaskForm):
    """Form for bulk editing matches"""
    court = StringField('Court Assignment', validators=[Optional(), Length(max=50)])
    scheduled_date = DateField('Scheduled Date', format='%Y-%m-%d', validators=[Optional()])
    scheduled_time = TimeField('Scheduled Time', format='%H:%M', validators=[Optional()])
    
    # Selection fields
    select_all = BooleanField('Select All', default=False)
    match_ids = FieldList(HiddenField('Match ID'), min_entries=0)
    selected_matches = FieldList(BooleanField('Select'), min_entries=0)
    
    # Confirmation step
    confirm = BooleanField('Confirm Changes', validators=[Optional()])
    
    preview = SubmitField('Preview Changes')

class BracketGenerationForm(FlaskForm):
    """Form for generating tournament brackets"""
    bracket_type = SelectField('Bracket Type', choices=[
        ('generate_groups', 'Generate Group Stage'),
        ('generate_knockout', 'Generate Knockout Stage')
    ], validators=[DataRequired()])
    
    use_seeding = BooleanField('Use Seeding for Bracket Generation', default=True)
    third_place_match = BooleanField('Include Third Place Match', default=True)
    
    submit = SubmitField('Generate Bracket')

class CategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[Length(max=100)])

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
                                   validators=[NumberRange(min=0)],
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
                                         FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!'),
                                        validate_file_size(max_size_mb=5)])

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
                                        FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!'),
                                        validate_file_size(max_size_mb=5)])
    
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
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!'),
        validate_file_size(max_size_mb=5)
    ])
    
    submit = SubmitField('Save Venue')


class VenueImageForm(FlaskForm):
    image = FileField('Venue Image', validators=[
        DataRequired(),
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!'),
        validate_file_size(max_size_mb=5)
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
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!'),
        validate_file_size(max_size_mb=5)
    ])
    banner_image = FileField('Banner Image', validators=[
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!'),
        validate_file_size(max_size_mb=5)
    ])
    
    submit = SubmitField('Save Sponsor')


class TournamentSponsorForm(FlaskForm):
    sponsors = FieldList(IntegerField('Sponsor ID'))
    sponsor_order = FieldList(IntegerField('Order'))
    
    submit = SubmitField('Save Sponsors')


class TournamentVenueForm(FlaskForm):
    venue_id = IntegerField('Venue ID', validators=[Optional()])
    
    submit = SubmitField('Save Venue')