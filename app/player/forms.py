from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, IntegerField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional, URL
from datetime import datetime

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
    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])
    partner_id = SelectField('Partner (for doubles)', coerce=int)
    submit = SubmitField('Register')

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
