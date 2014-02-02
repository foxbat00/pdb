from flask.ext.wtf import Form, TextField, BooleanField, SelectField, HiddenField, RadioField, DateField, SubmitField,fields, validators, IntegerField, NumberRange, Length
from flask.ext.wtf import InputRequired, Email, EqualTo, Optional
from models import *
from db import Base, session
from app import app



class WatchForm(Form):
    test = 'Ok'
