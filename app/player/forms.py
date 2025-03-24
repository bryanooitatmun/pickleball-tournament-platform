from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, TextAreaField, IntegerField, SelectField, SubmitField, HiddenField, EmailField, PasswordField, BooleanField, DecimalField, TelField, DateField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional, URL, EqualTo
from datetime import datetime, date
from app.models import Tournament, TournamentCategory, Registration, PlayerProfile, User, UserRole

class ProfileForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=100)])
    country = StringField('Country', validators=[DataRequired(), Length(max=100)])
    city = StringField('City', validators=[Length(max=100)])
    age = IntegerField('Age', validators=[NumberRange(min=5, max=99)])
    bio = TextAreaField('Bio')
    plays = SelectField('Plays', choices=[
        ('Right-handed', 'Right-handed'), 
        ('Left-handed', 'Left-handed')
    ])
    height = StringField('Height', validators=[Length(max=20)])
    paddle = StringField('Paddle', validators=[Length(max=100)])
    profile_image = FileField('Profile Picture', validators=[
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])
    action_image = FileField('Action Shot', validators=[
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])
    banner_image = FileField('Banner Image', validators=[
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])
    instagram = StringField('Instagram Link', validators=[Optional(), URL()])
    facebook = StringField('Facebook Link', validators=[Optional(), URL()])
    twitter = StringField('Twitter Link', validators=[Optional(), URL()])
    turned_pro = IntegerField('Turned Pro (Year)', validators=[
        NumberRange(min=1970, max=datetime.now().year)
    ])
    submit = SubmitField('Save Profile')

class RegistrationForm(FlaskForm):
    """Form for team registration"""
    tournament_id = HiddenField('Tournament ID')
    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])
    
    # Player 1 Fields
    player1_name = StringField('Player 1 Full Name', validators=[
        DataRequired(), 
        Length(min=2, max=100, message="Name must be between 2 and 100 characters")
    ])
    player1_email = EmailField('Player 1 Email', validators=[
        DataRequired(), 
        Email(message="Please enter a valid email address")
    ])
    player1_email_confirm = EmailField('Confirm Player 1 Email', validators=[
        DataRequired(),
        Email(message="Please enter a valid email address"),
        EqualTo('player1_email', message="Email addresses must match")
    ])
    player1_phone = TelField('Player 1 Phone', validators=[
        DataRequired(), 
        Length(min=8, max=20, message="Phone number must be between 8 and 20 characters")
    ])
    player1_dupr_id = StringField('Player 1 DUPR ID', validators=[
        DataRequired(),
        Length(min=2, max=50, message="DUPR ID must be between 2 and 50 characters")
    ])
    player1_date_of_birth = DateField('Player 1 Date of Birth', validators=[DataRequired()])
    player1_nationality = StringField('Player 1 Nationality', validators=[
        DataRequired(),
        Length(min=2, max=50, message="Nationality must be between 2 and 50 characters")
    ])
    
    # Player 2 Fields (conditional validators added in code)
    player2_name = StringField('Player 2 Full Name')
    player2_email = EmailField('Player 2 Email')
    player2_email_confirm = EmailField('Confirm Player 2 Email')
    player2_phone = TelField('Player 2 Phone')
    player2_dupr_id = StringField('Player 2 DUPR ID')
    player2_date_of_birth = DateField('Player 2 Date of Birth')
    player2_nationality = StringField('Player 2 Nationality')
    
    # Additional fields
    special_requests = TextAreaField('Special Requests', validators=[
        Optional(), 
        Length(max=500)
    ])
    
    # Agreements
    terms_agreement = BooleanField('Terms and Conditions', validators=[
        DataRequired(message="You must agree to the terms and conditions")
    ])
    liability_waiver = BooleanField('Liability Waiver', validators=[
        DataRequired(message="You must agree to the liability waiver")
    ])
    media_release = BooleanField('Media Release', validators=[
        DataRequired(message="You must agree to the media release")
    ])
    pdpa_consent = BooleanField('PDPA Consent', validators=[
        DataRequired(message="You must provide PDPA consent")
    ])
    
    def __init__(self, tournament, *args, **kwargs):
        super(RegistrationForm, self).__init__(*args, **kwargs)
        self.tournament = tournament
        
        # Populate the categories dropdown
        categories = [(c.id, c.name) for c in tournament.categories.order_by(TournamentCategory.display_order)]
        self.category_id.choices = categories
        
    def validate(self, extra_validators=None):
        """Custom validation to handle doubles vs singles categories"""
        if not super(RegistrationForm, self).validate(extra_validators=extra_validators):
            return False
            
        # Get selected category
        category = TournamentCategory.query.get(self.category_id.data)
        if not category:
            return False
            
        # For doubles categories, validate player 2 info
        if category.is_doubles():
            if not self.player2_name.data:
                self.player2_name.errors = ['Partner name is required for doubles events']
                return False
            if not self.player2_email.data:
                self.player2_email.errors = ['Partner email is required for doubles events']
                return False
            if not self.player2_phone.data:
                self.player2_phone.errors = ['Partner phone is required for doubles events']
                return False
            # Add more validation as needed
            
        return True

    def validate_category_id(self, field):
        """Validate the selected category exists in this tournament"""
        category = TournamentCategory.query.filter_by(
            id=field.data, tournament_id=self.tournament.id
        ).first()
        
        if not category:
            raise ValidationError('Invalid category selection')
        
        # Check if category is full
        if category.max_participants:
            current_registrations = Registration.query.filter_by(
                category_id=category.id, payment_status='paid'
            ).count()
            
            if current_registrations >= category.max_participants:
                raise ValidationError('This category is already full')
    
    def validate_player1_date_of_birth(self, field):
        """Validate player 1 date of birth"""
        if field.data > date.today():
            raise ValidationError('Date of birth cannot be in the future')
        
        # Check if the player meets age requirements for the selected category
        if self.category_id.data:
            category = TournamentCategory.query.get(self.category_id.data)
            if category and category.min_age:
                # Calculate age based on tournament start date
                age = self.tournament.start_date.year - field.data.year
                if (self.tournament.start_date.month, self.tournament.start_date.day) < (field.data.month, field.data.day):
                    age -= 1
                    
                if age < category.min_age:
                    raise ValidationError(f'Player 1 does not meet the minimum age requirement of {category.min_age} years')
            
            if category and category.max_age:
                # Calculate age based on tournament start date
                age = self.tournament.start_date.year - field.data.year
                if (self.tournament.start_date.month, self.tournament.start_date.day) < (field.data.month, field.data.day):
                    age -= 1
                    
                if age > category.max_age:
                    raise ValidationError(f'Player 1 exceeds the maximum age requirement of {category.max_age} years')
    
    def validate_player2_date_of_birth(self, field):
        """Validate player 2 date of birth"""
        if field.data > date.today():
            raise ValidationError('Date of birth cannot be in the future')
        
        # Check if the player meets age requirements for the selected category
        if self.category_id.data:
            category = TournamentCategory.query.get(self.category_id.data)
            if category and category.min_age:
                # Calculate age based on tournament start date
                age = self.tournament.start_date.year - field.data.year
                if (self.tournament.start_date.month, self.tournament.start_date.day) < (field.data.month, field.data.day):
                    age -= 1
                    
                if age < category.min_age:
                    raise ValidationError(f'Player 2 does not meet the minimum age requirement of {category.min_age} years')
            
            if category and category.max_age:
                # Calculate age based on tournament start date
                age = self.tournament.start_date.year - field.data.year
                if (self.tournament.start_date.month, self.tournament.start_date.day) < (field.data.month, field.data.day):
                    age -= 1
                    
                if age > category.max_age:
                    raise ValidationError(f'Player 2 exceeds the maximum age requirement of {category.max_age} years')


class TournamentRegistrationForm(FlaskForm):
    # Hidden fields
    tournament_id = HiddenField('Tournament ID')
    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])
    
    # Player fields (only required if user is not logged in)
    email = EmailField('Email', validators=[Optional(), Email(), Length(max=120)])
    full_name = StringField('Full Name', validators=[Optional(), Length(max=100)])
    phone = StringField('Phone Number', validators=[Optional(), Length(max=20)])
    country = StringField('Country', validators=[Optional(), Length(max=50)])
    city = StringField('City', validators=[Optional(), Length(max=50)])
    password = PasswordField('Password', validators=[Optional(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', 
                                    validators=[Optional(), EqualTo('password', message='Passwords must match')])
    
    #Player 2 fields
    email_2 = EmailField('Email', validators=[Optional(), Email(), Length(max=120)])
    full_name_2 = StringField('Full Name', validators=[Optional(), Length(max=100)])
    phone_2 = StringField('Phone Number', validators=[Optional(), Length(max=20)])
    country_2 = StringField('Country', validators=[Optional(), Length(max=50)])
    city_2 = StringField('City', validators=[Optional(), Length(max=50)])
    password_2 = PasswordField('Password', validators=[Optional(), Length(min=8)])
    confirm_password_2 = PasswordField('Confirm Password', 
                                    validators=[Optional(), EqualTo('password', message='Passwords must match')])

    # Registration-specific fields
    partner_id = SelectField('Partner (for doubles)', coerce=int, validators=[Optional()])
    dupr_rating = StringField('DUPR Rating', validators=[Optional(), Length(max=10)])
    emergency_contact = StringField('Emergency Contact', validators=[Optional(), Length(max=100)])
    emergency_phone = StringField('Emergency Contact Phone', validators=[Optional(), Length(max=20)])
    
    # Additional player info
    date_of_birth = StringField('Date of Birth', validators=[Optional(), Length(max=10)])
    gender = SelectField('Gender', choices=[('', 'Select Gender'), ('M', 'Male'), ('F', 'Female'), ('O', 'Other')], 
                        validators=[Optional()])
    shirt_size = SelectField('Shirt Size', 
                           choices=[('', 'Select Size'), ('XS', 'XS'), ('S', 'S'), ('M', 'M'), 
                                   ('L', 'L'), ('XL', 'XL'), ('XXL', 'XXL')],
                           validators=[Optional()])
    
    # Special requests
    special_requests = TextAreaField('Special Requests', validators=[Optional(), Length(max=500)])
    
    # Agreements
    terms_agreement = BooleanField('I agree to the rules and regulations of this tournament', 
                                 validators=[DataRequired()])
    liability_waiver = BooleanField('I acknowledge that pickleball involves risks and waive liability', 
                                  validators=[DataRequired()])
    
    def validate_email(self, email):
        if not self.is_authenticated:  # Only validate if creating a new user
            user = User.query.filter_by(email=email.data.lower()).first()
            if user:
                raise ValidationError('This email is already registered. Please log in instead.')
    
    # Custom validation function to be used in the route
    def validate_registration(self, is_authenticated):
        self.is_authenticated = is_authenticated
        
        # If not authenticated, validate all user fields
        if not is_authenticated:
            if not self.email.data:
                self.email.errors.append('Email is required')
                return False
            
            if not self.full_name.data:
                self.full_name.errors.append('Full name is required')
                return False
            
            if not self.password.data:
                self.password.errors.append('Password is required')
                return False
                
            if self.password.data != self.confirm_password.data:
                self.confirm_password.errors.append('Passwords must match')
                return False
        
        return True


class EquipmentForm(FlaskForm):
    brand = StringField('Brand', validators=[DataRequired(), Length(max=100)])
    name = StringField('Name', validators=[DataRequired(), Length(max=200)])
    image = FileField('Equipment Image', validators=[
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])
    buy_link = StringField('Buy Link', validators=[Optional(), URL()])
    submit = SubmitField('Add Equipment')

class SponsorForm(FlaskForm):
    name = StringField('Sponsor Name', validators=[DataRequired(), Length(max=100)])
    logo = FileField('Sponsor Logo', validators=[
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])
    link = StringField('Sponsor Website', validators=[Optional(), URL()])
    submit = SubmitField('Add Sponsor')

class PaymentForm(FlaskForm):
    """Form for payment proof upload"""
    payment_proof = FileField('Payment Proof', validators=[
        FileRequired(message="Please upload your payment proof"),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images only!')
    ])
    submit = SubmitField('Submit Payment')

