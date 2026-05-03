from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DateField, PasswordField, TelField, FileField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, ValidationError
from wtforms.widgets import TextArea
from datetime import datetime, date

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegisterForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    phone = TelField('Phone Number', validators=[Optional(), Length(max=20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

class LostItemForm(FlaskForm):
    item_name = StringField('Item Name', validators=[DataRequired(), Length(min=2, max=200)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=1000)])
    category = SelectField('Category', choices=[
        ('ID Card', 'ID Card'),
        ('Phone', 'Phone'),
        ('Bag', 'Bag'),
        ('Wallet', 'Wallet'),
        ('Keys', 'Keys'),
        ('Jewelry', 'Jewelry'),
        ('Electronics', 'Electronics'),
        ('Books', 'Books'),
        ('Clothing', 'Clothing'),
        ('Documents', 'Documents'),
        ('Other', 'Other')
    ], validators=[DataRequired()])
    location_lost = StringField('Location Lost', validators=[DataRequired(), Length(max=200)])
    date_lost = DateField('Date Lost', validators=[DataRequired()], default=date.today)
    image = FileField('Upload Image', validators=[Optional()])
    contact_info = StringField('Contact Information', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Report Lost Item')

class FoundItemForm(FlaskForm):
    item_name = StringField('Item Name', validators=[DataRequired(), Length(min=2, max=200)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=1000)])
    category = SelectField('Category', choices=[
        ('ID Card', 'ID Card'),
        ('Phone', 'Phone'),
        ('Bag', 'Bag'),
        ('Wallet', 'Wallet'),
        ('Keys', 'Keys'),
        ('Jewelry', 'Jewelry'),
        ('Electronics', 'Electronics'),
        ('Books', 'Books'),
        ('Clothing', 'Clothing'),
        ('Documents', 'Documents'),
        ('Other', 'Other')
    ], validators=[DataRequired()])
    location_found = StringField('Location Found', validators=[DataRequired(), Length(max=200)])
    date_found = DateField('Date Found', validators=[DataRequired()], default=date.today)
    image = FileField('Upload Image', validators=[Optional()])
    contact_info = StringField('Contact Information', validators=[Optional(), Length(max=500)])
    storage_location = StringField('Storage Location', validators=[Optional(), Length(max=200)])
    submit = SubmitField('Report Found Item')

class SearchForm(FlaskForm):
    query = StringField('Search', validators=[Optional(), Length(max=100)])
    category = SelectField('Category', choices=[
        ('', 'All Categories'),
        ('ID Card', 'ID Card'),
        ('Phone', 'Phone'),
        ('Bag', 'Bag'),
        ('Wallet', 'Wallet'),
        ('Keys', 'Keys'),
        ('Jewelry', 'Jewelry'),
        ('Electronics', 'Electronics'),
        ('Books', 'Books'),
        ('Clothing', 'Clothing'),
        ('Documents', 'Documents'),
        ('Other', 'Other')
    ])
    status = SelectField('Status', choices=[
        ('', 'All Status'),
        ('pending', 'Pending'),
        ('matched', 'Matched'),
        ('returned', 'Returned')
    ])
    submit = SubmitField('Search')

class MatchActionForm(FlaskForm):
    action = SelectField('Action', choices=[
        ('verify', 'Verify Match'),
        ('reject', 'Reject Match'),
        ('returned', 'Mark as Returned')
    ], validators=[DataRequired()])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=1000)])
    submit = SubmitField('Submit Action')

class UserEditForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    phone = TelField('Phone Number', validators=[Optional(), Length(max=20)])
    submit = SubmitField('Update Profile')

class PasswordChangeForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Change Password')
