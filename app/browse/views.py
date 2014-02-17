from flask import Blueprint, Response, render_template, flash, redirect, session, url_for, request, jsonify, abort
from app import app
from db import session, Base
from models import *
from datetime import datetime
from sqlalchemy import *
from app.browse.forms import BrowseForm
import json
from functools import wraps





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
	


#### Decorator for view functions to check for PJAX header
  ## returns 403 error if PJAX header not detected

def xpjax_only(view_function):
    @wraps(view_function)
    # the new, post-decoration function. Note *args and **kwargs here.
    def decorated_function(*args, **kwargs):
	if "X-PJAX" in request.headers:
            return view_function(*args, **kwargs)
        else:
	    app.logger.error('ERROR:  non-PJAX request to PJAX route')
            abort(403)
    return decorated_function


@mod.route('/browse/', methods=('GET',) )
def browse_view():
    return render_template('browse.html')


#### PJAX ####

@mod.route('/browse/', methods=('GET','POST') )
@xpjax_only		    # route must be outermost to work correctly
def search_query(query):
    max = 100
    query = request.args.get('query')
    afd = active_files('display_name')
    q = session.query(afd.c.display_name)\
	.filter( afd.c.display_name.ilike('%'+query+'%') )
    rs = q.limit(max).all()
    count = len(q.all())
    return render_template('pjax/results.html', results=sfrToList(rs), count=count, max=max)







#### AJAX  ####

"""
@mod.route('/browse/_search')
def ajax_search():
    search = request.args.get('term')
    afd = active_files('id','display_name')
    rs = session.query(afd.c.display_name, afd.c.id)\
	.filter( afd.c.display_name.ilike('%'+search+'%') )\
	.limit(2).all()
    if rs:
	js = lvdict(rs)
	app.logger.debug("returning...%d\n\n %s" % (len(rs), js))
	return json.dumps(js)
    else:
	return None

"""
    



