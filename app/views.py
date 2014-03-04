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

from helpers import *




"""
def getFacetString(taglist):
    tagstring = []
    for i in range (len(taglist)):
	tagstring.append( '"'+str(taglist[i].id) +'":"'+taglist[i].name+'"')
	if i < len(taglist) -1: # not last
	    tagstring.append(',')

    tagstring = ''.join(tagstring)
    return tagstring
"""


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
		  .join(FileInst, FileInst.file_id == File.id) \
		.filter(Scene.wordbag.ilike('%'+query+'%') ) \
		.filter(FileInst.deleted_on == None, FileInst.marked_delete == False) 
# TODO: add a checkbox to results page that includes deleted items, flag deleted items with pill
# or include a separate list at the bottom of deleted items, or something like that
	    rs = q.limit(max).all()
	    count = len(q.all())
	    return render_template('pjax/results.html', results=rs, count=count, max=max, query=rawquery)
    return redirect('/')



##### TODO:

# rename facetnames 
# refactor to support autocomplete, integrate with select2 






# used to get the tags, stars, etc. for autocomplete
@app.route('/facet/<facet>', methods=('GET', 'POST'))
def get_facet(facet):
    if request.is_xhr:
	app.logger.debug("get facet for facet %s" % facet)
	
	tbl = getattr(models, facet.lower().capitalize()) # Tag
	if not tbl:
	    app.logger.debug('not found: %s' % facet)
	    abort()

	if 'searchq' in request.args:
	    app.logger.debug("search")
	    search = request.args.get('searchq')
	    rs = session.query(tbl) \
		.filter( tbl.name.ilike(search+'%') ) \
		.limit(10).all()
	elif 'scene_id' in request.args:
	    app.logger.debug("scene lookup")
	    sid = request.args.get('scene_id')
	    linktbl = getattr(models,'Scene'+tbl.lower().capitalize()) # SceneTag
	    rs = session.query(tbl) \
		.join(linktbl, getattr(linktbl,facet.lower()+'_id') == tbl.id) \
		.filter(linktbl.scene_id == sid).all()

	else:
	    app.logger.debug('ERROR - nothing in args  recognized')
	    abort()


	if rs:
	    js = jsonifyList(rs)
	    app.logger.debug("returning...%d results:\n\n %s" % (len(rs), js))
	    return js
	else:
	    app.logger.debug("no results found, returning ERROR")
	    return json.dumps('{}') 
    else:
	app.logger.debug("no XHR header")
	app.logger.debug("headers received:  %s" % request.headers)
	return redirect('/')





# used by both the sidebar to get scene details and by sidebar ajax for getting things (to see if they exist mainly)
@app.route('/get/<thing>/<id>', methods=('GET', 'POST'))
def get_jax(thing, id):
    app.logger.debug("inside get_jax")
    if "X-PJAX" in request.headers:			### PJAX only
	app.logger.debug("xjax detected ")
	if thing and is_number(id):
	    id = int(id)
	    app.logger.debug("in get_jax for thing %s and id %d" % (thing, id))
	    tbl = getattr(models, thing.lower().capitalize())
	    o = session.query(tbl).get(id)
	    # scenes
	    if thing == 'scene':    
		deleted = o.isDeleted()
		facets = {}
		file_insts = session.query(FileInst).join(File, FileInst.file_id == File.id) \
		    .join(SceneFile, File.id ==SceneFile.file_id) \
		    .filter(SceneFile.scene_id == id).all()
		taglist = session.query(Tag) \
		    .select_from(SceneTag) \
		    .join(Tag, Tag.id == SceneTag.tag_id) \
		    .filter(SceneTag.scene_id == o.id) \
		    .all()
		#facets['taglist'] = jsonifyList(taglist)
		facets['alltags'] = jsonifyList(session.query(Tag).all())
		facets['thesetags'] = ','.join(str(x.name) for x in taglist)
		return render_template('pjax/sidebar.html',  \
		    scene=o, deleted=deleted, file_insts=file_insts, facets=facets)
	    else:
		app.logger.debug("get not yet implemented for type %s" % thing)
	else:   
	    app.logger.debug("XPJAX detected, but no id offered in url or id was not a number (q by str not yet)")
    elif request.is_xhr:
	tbl = getattr(models,thing.lower().capitalize())
	o = None
	# try to retrieve 
	if is_number(id):
	    id = int(id)
	    o = session.query(tbl).get(id)
	else:
	    name = id
	    o = session.query(tbl).filter(tbl.name.ilike(name)).first()
	# prepare response
	if o:
	    # see http://stackoverflow.com/questions/7102754/jsonify-a-sqlalchemy-result-set-in-flask
	    return o.json()
	else:
	    return json.dumps('')
    else:
	return redirect('/')
		    


# used for the sidebar to edit scene info
@app.route('/update/<thing>/<col>/<value>', methods=('GET','POST') )
def update_jax(thing, col, value):
    app.logger.debug("inside update_pjax")
    if "X-PJAX" in request.headers or "XMLHttpRequest" in request.headers:
	app.logger.debug("xjax detected ")
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
		    


# used for adding stars, tags, etc and the corresponding mapping entries to scene_*
@app.route('/add/<thing>/', methods=('POST',) )
def add_jax(thing):

    app.logger.debug("inside add")

    if  request.is_xhr:  # in > or
	app.logger.debug("xjax detected ")
	if thing:
	    app.logger.debug("received req = #%s#" % request)
	    app.logger.debug("received request.data = #%s#" % request.data)
	    app.logger.debug("received json.data = #%s#" % request.json)
	    #dct = json.loads(request.data)
	    dct = request.get_json()
	    app.logger.debug("json.data as dict = #%s#" % dct)

	    tbl = getattr(models, thing)
	    q = session.query(tbl)
	    for k,v in dct.iteritems():
		q = q.filter(getattr(tbl,k.lower())==v)
	    ex = q.first()
	    app.logger.debug("translated query:= %s" % q)
	    if not ex:
		new = tbl(**dct)
		app.logger.debug("adding new object: %s" % new)
		session.add(new)
		session.commit()
		return json.dumps('')
	    else:
		app.logger.debug("add failed because existing")
		return json.dumps('')
	else: 
	    app.logger.debug("XPJAX detected, but no thing or col or value offered in url")
    return redirect('/')
		    

