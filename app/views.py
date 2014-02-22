from flask import Blueprint, Response, render_template, flash, redirect, session, url_for, request, jsonify, abort
from app import app
from db import session, Base
from models import *
from datetime import datetime
from sqlalchemy import *
from app.forms import BrowseForm
import json
from functools import wraps
from app.decorators import xpjax_only
import shlex







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



@app.route('/test/', methods=('GET','POST') )
def test_view():
    return render_template('test.html')

@app.route('/browse/', methods=('GET','POST') )
def browse_view():
    app.logger.debug("in browse_view")
    if "X-PJAX" in request.headers:
	app.logger.debug("xpjax detected ")
	if "query" in request.values:
	    rawquery = request.values.get('query')
	    app.logger.debug("query = #%s#" % rawquery)
	    query = percentSeparator(rawquery)
	    max = 100
	    q = session.query(Scene) \
		.join(SceneFile, SceneFile.scene_id == Scene.id) \
		.join(File, File.id == SceneFile.file_id) \
		.join(FileInst, FileInst.file == File.id) \
		.filter(Scene.display_name.ilike('%'+query+'%') ) \
		.filter(FileInst.deleted_on == None, FileInst.marked_delete == False) 
# TODO: add a checkbox to results page that includes deleted items, flag deleted items with pill
# or include a separate list at the bottom of deleted items, or something like that
	    rs = q.limit(max).all()
	    count = len(q.all())
	    return render_template('pjax/results.html', results=rs, count=count, max=max, query=rawquery)
    #return render_template('browse.html')
    return redirect('/')


@app.route('/scene_deets/<int:sid>', methods=('GET', 'POST'))
def scene_deets_view(sid):
    app.logger.debug("inside scene_deets")
    if "X-PJAX" in request.headers:
	app.logger.debug("xpjax detected ")
	if sid:
	    app.logger.debug("in scene_deets for sid %d" % sid)
	    s = session.query(Scene).get(sid)
	    deleted = s.isDeleted()
	    file_insts = session.query(FileInst).join(File, FileInst.file == File.id) \
		.join(SceneFile, File.id ==SceneFile.file_id) \
		.filter(SceneFile.scene_id == s.id).all()
	    return render_template('pjax/sidebar.html', scene=s, deleted=deleted, file_insts=file_insts)
	else: 
	    app.logger.debug("XPJAX detected, but no sid offered in url")
    return redirect('/')
		    
	    
