from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField,SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length,Regexp

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    remember = BooleanField('I agree to the Terms & Conditions', validators=[DataRequired()])
    submit = SubmitField('Log In')


class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Send OTP')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired(),Length(min=6),Regexp(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])',message="Password must include uppercase, lowercase, digit, and special character")])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(),EqualTo('password', message="Passwords must match")])
    submit = SubmitField('Reset Password')

class RegistrationForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=50),Regexp(r'^[A-Za-z ]+$', message="Name must contain only letters and spaces")])
    email = StringField('Email', validators=[DataRequired(), Email(message="Invalid email format"),Regexp(r'^\S+@\S+\.\S+$', message="Invalid email format")])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6),Regexp(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{6,}$',message="Password must include uppercase, lowercase, digit, and special character")])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message="Passwords must match")])
    accept_terms = BooleanField('I agree to the Terms & Conditions', validators=[DataRequired()])
    submit = SubmitField('Register')    


# class HintAnswerForm(FlaskForm):
#     hint_answer = StringField('Answer to Hint Question', validators=[DataRequired(), Length(max=100)])
#     password = PasswordField('New Password', validators=[DataRequired(),Length(min=6),Regexp(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])',message="Password must include uppercase, lowercase, digit, and special character")])
#     confirm_password = PasswordField('Confirm Password', validators=[DataRequired(),EqualTo('password', message="Passwords must match")])
#     submit = SubmitField('Reset Password')
