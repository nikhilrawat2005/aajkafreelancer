from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileSize
from wtforms import StringField, PasswordField, BooleanField, TextAreaField, SelectField
from wtforms.validators import DataRequired, EqualTo, Length, ValidationError, Optional
from app.data.services_data import ALL_SKILLS

class PasswordLoginForm(FlaskForm):
    login_input = StringField('Email or Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])


class CompleteProfileForm(FlaskForm):
    """Form for completing profile after Google Sign-In (email from Google). Password is optional."""
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=100)])
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    college_name = SelectField('College', choices=[('ABES Engineering College', 'ABES Engineering College')],
                               validators=[DataRequired()])
    year = SelectField('Year', choices=[
        ('First Year', 'First Year'),
        ('Second Year', 'Second Year'),
        ('Third Year', 'Third Year'),
        ('Fourth Year', 'Fourth Year')
    ], validators=[DataRequired()])
    class_name = SelectField('Branch', choices=[
        ('CSE', 'CSE'),
        ('CSE (AIML)', 'CSE (AIML)'),
        ('ME', 'ME'),
        ('CS', 'CS'),
        ('ECE', 'ECE'),
        ('CSE (DS)', 'CSE (DS)')
    ], validators=[DataRequired()])
    section = StringField('Section', validators=[DataRequired()])
    phone_number = StringField('Phone Number', validators=[DataRequired(), Length(max=20)])
    short_bio = TextAreaField('Short Bio', validators=[Length(max=500)])
    is_worker = BooleanField('I want to offer my skills')
    skills = TextAreaField('Skills (comma separated)', validators=[Optional(), Length(max=500)])
    password = PasswordField('Set Password (optional)', validators=[Optional(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[Optional(), EqualTo('password')])

    def validate_section(form, field):
        branch = form.class_name.data
        if branch in ['CSE', 'CSE (AIML)', 'CSE (DS)']:
            allowed = [str(i) for i in range(11, 29)]
        else:
            allowed = ['A', 'B', 'C']
        if field.data not in allowed:
            raise ValidationError(f'Section must be one of: {", ".join(allowed)}')

    def validate_skills(form, field):
        if form.is_worker.data and not field.data:
            raise ValidationError('Please list your skills.')

    def validate_confirm_password(form, field):
        # If password is set, confirmation becomes required
        if form.password.data and not field.data:
            raise ValidationError('Please confirm your password.')


class EditProfileForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=100)])
    college_name = SelectField('College', choices=[('ABES Engineering College', 'ABES Engineering College')],
                               validators=[DataRequired()])
    year = SelectField('Year', choices=[
        ('First Year', 'First Year'),
        ('Second Year', 'Second Year'),
        ('Third Year', 'Third Year'),
        ('Fourth Year', 'Fourth Year')
    ], validators=[DataRequired()])
    class_name = SelectField('Branch', choices=[
        ('CSE', 'CSE'),
        ('CSE (AIML)', 'CSE (AIML)'),
        ('ME', 'ME'),
        ('CS', 'CS'),
        ('ECE', 'ECE'),
        ('CSE (DS)', 'CSE (DS)')
    ], validators=[DataRequired()])
    section = StringField('Section', validators=[DataRequired()])

    phone_number = StringField('Phone Number', validators=[DataRequired(), Length(max=20)])
    short_bio = TextAreaField('Short Bio', validators=[Length(max=500)])
    is_worker = BooleanField('I offer my skills')
    skills = TextAreaField('Skills (comma separated)', validators=[Optional(), Length(max=500)])

    # Profile image field
    profile_image = FileField('Profile Picture', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images only!'),
        FileSize(max_size=10 * 1024 * 1024)
    ])

    def validate_section(form, field):
        branch = form.class_name.data
        if branch in ['CSE', 'CSE (AIML)', 'CSE (DS)']:
            allowed = [str(i) for i in range(11, 29)]
        else:
            allowed = ['A', 'B', 'C']
        if field.data not in allowed:
            raise ValidationError(f'Section must be one of: {", ".join(allowed)}')

    def validate_skills(form, field):
        if form.is_worker.data and not field.data:
            raise ValidationError('Please list your skills.')


class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])