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
def lvdictPairs(labelsvalues):
    js = []
    for (l,v) in labelsvalues:
	js.append({"label":l,"value":v})
    return js
	
# autocomplete label value dicts to feed jquery
def lvdict(mylist):
    js = []
    for v in mylist:
	js.append({"label":v,"value":v})
    return js
	


def getFacetString(taglist):
    tagstring = []
    for i in range (len(taglist)):
	tagstring.append( str(taglist[i].id) +":"+taglist[i].name)
	if i < len(taglist) -1: # not last
	    tagstring.append(',')

    tagstring = ''.join(tagstring)
    return tagstring


# replace whitespace not enclosed in quotes with % for sql searching
def percentSeparator(str):
    return '%'.join(['"{0}"'.format(fragment) if ' ' in fragment else fragment
	for fragment in shlex.split(str)])

def is_number(s):
    try:
        int(s)
        return True
    except ValueError:
        return False

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
		.filter(Scene.wordbag.ilike('%'+query+'%') ) \
		.filter(FileInst.deleted_on == None, FileInst.marked_delete == False) 
# TODO: add a checkbox to results page that includes deleted items, flag deleted items with pill
# or include a separate list at the bottom of deleted items, or something like that
	    rs = q.limit(max).all()
	    count = len(q.all())
	    return render_template('pjax/results.html', results=rs, count=count, max=max, query=rawquery)
    return redirect('/')



# used to get the tags, stars, etc. for autocomplete
@app.route('/facetnames/<facet>', methods=('GET', 'POST'))
def get_facet_names(facet):
    if request.is_xhr:
	app.logger.debug("get facet names for facet %s" % facet)
	search = request.args.get('q')
	if not search:
	    app.logger.debug('ERROR - no search term detected')
	    abort()
	tbl = getattr(models, facet.lower().capitalize())
	rs = session.query(tbl.name) \
	    .filter( tbl.name.ilike(search+'%') ) \
	    .limit(10).all()
	if rs:
	    #js = lvdict(rs)
	    #return json.dumps(js)
	    return rs.json()
	    app.logger.debug("returning...%d results:\n\n %s" % (len(rs), js))
	else:
	    app.logger.debug("no results found, returning ERROR")
	    return json.dumps('ERROR') 
    else:
	app.logger.debug("no XHR header")
	app.logger.debug("headers received:  %s" % request.headers)
	return redirect('/')





# used by both the sidebar to get scene details and by sidebar ajax for getting things (to see if they exist mainly)
@app.route('/get/<thing>/<id>', methods=('GET', 'POST'))
def get_jax(thing, id):
    app.logger.debug("inside get_pjax")
    if "X-PJAX" in request.headers:			### PJAX only
	app.logger.debug("xjax detected ")
	if thing and is_number(id):
	    id = int(id)
	    app.logger.debug("in get_pjax for thing %s and id %d" % (thing, id))
	    tbl = getattr(models, thing.lower().capitalize())
	    o = session.query(tbl).get(id)
	    # scenes
	    if thing == 'scene':    
		deleted = o.isDeleted()
		facets = {}
		file_insts = session.query(FileInst).join(File, FileInst.file == File.id) \
		    .join(SceneFile, File.id ==SceneFile.file_id) \
		    .filter(SceneFile.scene_id == id).all()
		taglist = session.query(Tag) \
		    .select_from(SceneTag) \
		    .join(Tag, Tag.id == SceneTag.tag_id) \
		    .filter(SceneTag.scene_id == o.id) \
		    .all()
		tagstring = getFacetString(taglist)
		facets['taglist'] = tagstring
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
	    return o._json()
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
	    dct = get_json()
	    tbl = getattr(models, thing.lower().capitalize())
	    q = session.query(tbl)
	    for (k,v) in dct:
		q.filter(getattr(tbl,k.lower())==v)
	    ex = q.first()
	    if not ex:
		new = tbl(**dct)
		session.add(new)
		session.commit(new)
		return json.dumps('')
	    else:
		app.logger.debug("add failed because existing")
		return json.dumps('')
	else: 
	    app.logger.debug("XPJAX detected, but no thing or col or value offered in url")
    return redirect('/')
		    

