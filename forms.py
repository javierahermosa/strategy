from flask.ext.wtf import Form, RecaptchaField
from wtforms import TextField, PasswordField, validators
from wtforms.validators import Required, EqualTo, Email, optional, ValidationError
from werkzeug.datastructures import MultiDict
import MySQLdb 
from util import *

def strip_string(string):
    if string == None: pass
    else: return string.strip()

def is_symbol(form, field):
    symbols = get_symbols()
    if field.data not in symbols:
        raise ValidationError('Stock must be in S&P500')
             
class InputForm(Form):
    stock = TextField('Stock', [Required(), is_symbol])
    transaction = TextField('Transaction')
    strategy = TextField('Strategy')
    email = TextField('Email address', [optional(), Email()], filters=[strip_string])
    