#!/usr/bin/env python
from sqlalchemy import *
import sqlalchemy.dialects as postgres
from sqlalchemy.orm import scoped_session, sessionmaker
import datetime
import dateutil.parser as dup
import re, sys, os
from threading import Thread
from Queue import Queue
import logging 
from contextlib import contextmanager
from functools import wraps
from twisted.internet.threads import deferToThread


# globals
logfile = 'logs/log.txt'



# threading queues

# set up db
from db import *
from models import *
import models # needed for getattr magic
from util import *
session = scoped_session(sessionmaker(autocommit=False, autoflush=True, bind=engine))

# logging
format = "%(levelname)s (%(threadName)s): %(message)s"
logging.basicConfig(level=logging.DEBUG, format=format)
logger = logging.getLogger(__name__)
logoutput = logging.FileHandler(logfile, mode='w')
logoutput.setLevel(logging.DEBUG)
logoutput.setFormatter(logging.Formatter(format))
logger.addHandler(logoutput)

#logger.setLevel(logging.INFO)





# collect files that have no scene
for file in session.query(File).filter(_not(exists().where(SceneFile.file_id == File.id)))
    yield_per(200):


    # make tentative scene
    scene = Scene(file.name)
    session.add(scene)
    session.flush()
    sf = SceneFile(scene.id, file.id)
    session.add(sf)
    session.flush()
    

    wordbag = session.query(func.get_words_for_scene(scene.id)).first()

    # iterate over alias_rules
    for a in alias_rules:

	# for each potential target of the alias
	for tb in ['AliasTag', 'AliasStar', 'AliasLabel', 'AliasSeries']:
	    table = getattr(models,tb)    # requires import models, not from models import...

	    # get the potential targets for this alias
	    targets = session.query(table).filter(table.alias_id == a.alias_id).all()
	    if not targets:
		continue

	    cond = a.condition
	    match = None    
	    if a.condition_type == 'REGEX':
		flags = None
		if not a.case_sensitive:
		    flags = re.I
		match = re.search(cond, wordbag, flags)
	    elif tr.condition_type == 'TSVECTOR':
		match = session.query(Scene).filter(Scene.tsvector.op('@@')(func.plainto_tsquery(cond)).first()
	    else:
		logger.error("unrecognized alias_rule.condition_type: %s" % tr.condition_type)
		continue
	
	    

	    # not > and > or
	    if match and not a.exclude   or    not match and a.exclude:
		# add the association between the target and the scene
		for t in targets:  
		    # need to lookup the tag/star/label/series id from the Alias* table+'_id'
		    col = re.sub('^Alias', '', tb).lower()+'_id'
		    target_id = getattr(t,col)
		    existing = session.query(table).filter(table.scene_id == scene.id, table.col == target_id)
			.first()
		    if not existing:
			newrec = table(scene.id, target_id)
			session.add(newrec)
			session.flush()

		    
    # iterate over implications

		    
		
	




    # iterate over alias_implications 











	def add(scene, tag_id):
	    if session.query(SceneTag).filter(SceneTag.scene_id == scene.id, SceneTag.tag_id == tag_id).first():
		logger.debug("tag already exists - skipping")
		return
	    else:
		st = SceneTag(scene.id, tag_id)
		session.add(st)
		session.flush()
	


