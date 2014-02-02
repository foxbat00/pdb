from flask import Blueprint, Response, render_template, flash, redirect, session, url_for, request
from app import app
from db import session, Base
from models import *
from datetime import datetime
from sqlalchemy import *
from app.watch.forms import WatchForm




mod = Blueprint('watch', __name__)


# turn a sqlalchemy row into a dict by field-name
row2dict = lambda r: {c.name: getattr(r,c.name) for c in r.__table__.columns}
    
@mod.route('/watch/', methods=('GET',))
def watch_view():
    form = WatchForm(request.form)
    stream = None
    return render_template('watch.html', form=form)


