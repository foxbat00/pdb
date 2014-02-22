from flask import Blueprint, Response, render_template, flash, redirect, session, url_for, request, jsonify, abort
from app import app
from db import session, Base
from models import *
import models # needed for getattr magic
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

@app.route('/search/words/scene/', methods=('GET','POST') )
def search_view():
    app.logger.debug("in search_view")
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
    return redirect('/')


@app.route('/get/<thing>/<int:id>', methods=('GET', 'POST'))
def get_pjax(thing, id):
    app.logger.debug("inside get_pjax")
    if "X-PJAX" in request.headers:
	app.logger.debug("xpjax detected ")
	if thing and id:
	    app.logger.debug("in get_pjax for thing %s and id %d" % (thing, id))
	    tbl = getattr(models, thing.lower().capitalize())
	    o = session.query(tbl).get(id)
	    # scenes
	    if thing == 'scene':    
		deleted = o.isDeleted()
		file_insts = session.query(FileInst).join(File, FileInst.file == File.id) \
		    .join(SceneFile, File.id ==SceneFile.file_id) \
		    .filter(SceneFile.scene_id == id).all()
		tags = session.query(Tag.name) \
		    .select_from(SceneTag) \
		    .join(Tag, Tag.id == SceneTag.tag_id) \
		    .filter(SceneTag.scene_id == o.id) \
		    .all()
		    
		return render_template('pjax/sidebar.html', scene=o, deleted=deleted, file_insts=file_insts)
	    else:
		app.logger.debug("get not yet implemented for type %s" % thing)
	else: 
	    app.logger.debug("XPJAX detected, but no id offered in url")
    return redirect('/')
		    


@app.route('/update/<thing>/<col>/<value>', methods=('GET','POST') )
def update_pjax(thing, col, value):
    app.logger.debug("inside update_pjax")
    if "X-PJAX" in request.headers:
	app.logger.debug("xpjax detected ")
	if thing and col and value:
	    app.logger.debug("in update_pjax for thing %s, col %s, and value %s" % (thing, col, value))
	    tbl = getattr(models, thing.lower.capitalize())
	    o = session.query(tbl).get(id)
	    if o and setattr(o,col.lower(),value):
		# TODO consider cleaning up value first according to whatever scheme thing requires
		return True
	    else:
		app.logger.debug("update failed")
		return False
	else: 
	    app.logger.debug("XPJAX detected, but no thing or col or value offered in url")
    return redirect('/')
		    

    
    return False
