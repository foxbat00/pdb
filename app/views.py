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
	if "query" in request.values:  # TODO: should be just request?
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




"""

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

"""



# used by both the sidebar to get scene details and by sidebar ajax for getting things (to see if they exist mainly)
@app.route('/getpjax/<thing>/<id>', methods=('GET', 'POST'))
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
		for fac in ("Tag", "Star"):

		    factbl = getattr(models, fac)
		    ltbl = getattr(models, 'Scene'+fac)

		    facets['all'+fac.lower()+'s'] = jsonifyList(session.query(factbl).all())


		    file_insts = session.query(FileInst).join(File, FileInst.file_id == File.id) \
			.join(SceneFile, File.id ==SceneFile.file_id) \
			.filter(SceneFile.scene_id == id).all()

		    taglist = session.query(factbl) \
			.select_from(ltbl) \
			.join(factbl, factbl.id == getattr(ltbl, fac.lower()+'_id')) \
			.filter(ltbl.scene_id == o.id) \
			.all()

		    facets['these'+fac.lower()+'s'] = ','.join(str(x.id) for x in taglist)

		app.logger.debug("facets = %s", facets)
		return render_template('pjax/sidebar.html',  \
		    scene=o, deleted=deleted, file_insts=file_insts, facets=facets)

	    else:
		app.logger.debug("get not yet implemented for type %s" % thing)
	else:   
	    app.logger.debug("XPJAX detected, but no id offered in url or id was not a number (q by str not yet)")
    else:
	return redirect('/')
		    



# used for adding stars, tags, etc and the corresponding mapping entries to scene_*
@app.route('/json/<action>/<thing>/', defaults={'id':None, 'col':None, 'value': None}, methods=('GET','POST') )
@app.route('/json/<action>/<thing>/<id>', defaults={'col':None, 'value':None}, methods=('GET', 'POST') )
@app.route('/json/<action>/<thing>/<col>/<value>', defaults={'id':None}, methods=('GET','POST') )
def json_action(action, thing, id=None, col=None, value=None):

    app.logger.debug("inside json")

    if not request.is_xhr:  # in > or
	app.logger.debug("no xhr header detected ")
	return redirect('/')

    app.logger.debug("received req = #%s#" % request)
    if 'data' in request.values:
	app.logger.debug("received request.data = #%s#" % request.data)
    else:
	app.logger.debug("no data content received")

    # not > and > or
    if not thing or not action:
	app.logger.debug("thing or action missing")
	abort()
    app.logger.debug("action=%s, thing=%s" % (action, thing) )




    # add doesn't require json or data
    if action == 'get' and id:
	tbl = getattr(models,thing)
	o = None

	# try to retrieve 
	if is_number(id):
	    id = int(id)
	    o = session.query(tbl).get(id)
	else:
	    name = id
	    o = session.query(tbl).filter(tbl.name.ilike(name)).first()


	if o:
	    # see http://stackoverflow.com/questions/7102754/jsonify-a-sqlalchemy-result-set-in-flask
	    return o.json()
	else:
	    return json.dumps('{}')




    # set up the jason response
    if hasattr(request, 'json'):
	app.logger.debug("received json.data = #%s#" % request.json)
	#dct = json.loads(request.data)
	dct = request.get_json()
	app.logger.debug("json.data as dict = #%s#" % dct)
    else:
	app.logger.debug("no json received")
	abort()




    if action == 'add' or action == 'delete':

	tbl = getattr(models, thing)
	q = session.query(tbl)
	aliases = None
	for k in dct.keys():
	    if k == 'aliases':
		aliases = dct[k]
		del dct[k]
	    else: 
		q = q.filter(getattr(tbl,k.lower())==dct[k])
	ex = q.first()

	app.logger.debug("translated query:= %s" % q)
	app.logger.debug("aliases received = %s" % aliases)
	if action == 'add':
	    if not ex:
		new = tbl(**dct)
		session.add(new)
		session.commit()
		app.logger.debug("adding new object: %s" % new)
		app.logger.debug("returning: %s" % new.json() )

		if aliases:
		    for a in [x.strip().lower() for x in aliases.split(',')]:
			exa = session.query(Alias).filter(Alias.name == a).first()
			if not exa:
			    exa = Alias(a)
			    session.add(exa)
			    session.commit()
			    app.logger.debug("added: %s" % exa)
			    linktbl = getattr(models, 'Alias'+thing)
			    lt = linktbl(exa.id, new.id)
			    session.add(lt)
			    session.commit()
			    app.logger.debug("added: %s" % lt)
		return new.json()
	    else:
		app.logger.debug("add failed because existing")
		return json.dumps('{}')
	elif action == 'delete':
	    if ex:
		session.delete(ex)
		session.commit()
	    else:
		app.logger.debug("existing not found for delete")
	    return json.dumps('{}')
		    


    elif action == 'update':
	    app.logger.debug("in update")
	    tbl = getattr(models, thing.lower().capitalize())
	    pk = dct['pk']
	    del dct['pk'] # remove so we don't pick it up later
	    o = session.query(tbl).get(pk)
	    if o: 
		# TODO consider cleaning up value first according to whatever scheme thing requires
		#setattr(o,dct['name'].lower(), dct['value'])
		for k,v in dct.iteritems():
		    setattr(o,k.lower(), v)
		session.commit()
		app.logger.debug("set %s %s:  %s" % (thing, pk, dct))
		return json.dumps('{"success": true}')
	    else:
		app.logger.debug("update failed")
		return json.dumps('{"success": false, "msg": "Update failed: not found"}')

    else:
	app.logger.debug("action not understood")
	abort()



