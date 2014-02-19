from flask import Blueprint, Response, render_template, flash, redirect, session, url_for, request, jsonify, abort
from app import app
from db import session, Base
from models import *
from datetime import datetime
from sqlalchemy import *
from app.browse.forms import BrowseForm
import json
from functools import wraps
from app.browse.decorators import xpjax_only
import shlex





mod = Blueprint('browse', __name__)

from sqlalchemy.sql import column
# snippet to use in querying against only active files for jquery
def active_files(*fields):
    if not fields:
	return select([File]).select_from(func.active_files()).alias('active_files')
    else:
	field_list = []
	for f in fields:
	    field_list.append(column(f))
	return select(field_list).select_from(func.active_files()).alias('active_files')
	    

# turn single-field query results into straight list
def sfrToList(rs):
    return map(lambda l: l[0],rs)
	    

# turn a sqlalchemy row into a dict by field-name
row2dict = lambda r: {c.name: getattr(r,c.name) for c in r.__table__.columns}
    

# autocomplete label value dicts to feed jquery
def lvdict(labelsvalues):
    js = []
    for (l,v) in labelsvalues:
	js.append({"label":l,"value":v})
    return js
	

# replace whitespace not enclosed in quotes with % for sql searching
def percentSeparator(str):
    return '%'.join(['"{0}"'.format(fragment) if ' ' in fragment else fragment
	for fragment in shlex.split(str)])



@mod.route('/test/', methods=('GET','POST') )
def browse_view():
    return render_template('test.html')

@mod.route('/browse/', methods=('GET','POST') )
def browse_view():
    app.logger.debug("in browse_view")
    if "X-PJAX" in request.headers:
	app.logger.debug("xpjax detected ")
	if "query" in request.values:
	    rawquery = request.values.get('query')
	    app.logger.debug("query = #%s#" % rawquery)
	    query = percentSeparator(rawquery)
	    max = 100
	    afd = active_files('display_name')
	    q = session.query(afd.c.display_name)\
		.filter( afd.c.display_name.ilike('%'+query+'%') )
	    rs = q.limit(max).all()
	    count = len(q.all())
	    return render_template('pjax/results.html', results=sfrToList(rs), count=count, max=max, query=rawquery)
    return render_template('browse.html')

