from flask import Blueprint, Response, render_template, flash, redirect, session, url_for, request
from app import app
from db import session, Base
from models import *
from datetime import datetime
from sqlalchemy import *
from app.browse.forms import BrowseForm




mod = Blueprint('browse', __name__)


# turn a sqlalchemy row into a dict by field-name
row2dict = lambda r: {c.name: getattr(r,c.name) for c in r.__table__.columns}
    
@mod.route('/browse/', methods=('GET',))
def browse_view():
    form = BrowseForm(request.form)
    return render_template('browse.html', form=form)


#### AJAX  ####


@app.route('/_search')
def ajax_search():
    search = request.args.get('search')
    # TODO: fix m
    



