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
import shlex
from itertools import tee, izip


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




# break a string down into words and quote-enclosed phrases
def tokenize(string):
    return ['"{0}"'.format(fragment) if ' ' in fragment else fragment for fragment in shlex.split(string)]

# return match if single or double-enclosed quote phrase detected
def isQuoteEnclosed(string):
    return re.search(r'(["\'])(?:(?=(\\?))\2.)*?\1',string)

# break a string down into words (alphanum) and ignore quotes and all other non-alphas
def mulch(string):
    return re.findall(r'\w+',string)

# iterate pairwise through a list  "s -> (s0,s1), (s1,s2), (s2, s3), ..."
def pairwise(iterable):
        a, b = tee(iterable)
	next(b, None)
	return izip(a, b)

# if small is a subsequence of big, returns (start, end+1) of sequence occurence
def contains(small, big):
    for i in xrange(len(big)-len(small)+1):
        for j in xrange(len(small)):
	    if type(big[i+j]) == type('') == type(small[j]):
		if big[i+j].lower() != small[j].lower():
		    break
	    else:
		if big[i+j] != small[j]:
		    break
        else:
            return i, i+len(small)
    return False




# searches for condition in mulched_wordbag
def wordmatch(condition, mulched_wordbag):
    match = True
    terms = tokenize(condtion)		    
    for t in terms:
	if not isQuoteEnclosed(t):
	    if t not in mulched_wordbag:
		return None
	else:
	    if not contains(mulch(t),mulched_wordbag):
		return None
		
		

# add association  to  table (SceneTag, SceneStar, etc)'s target id and the scene

def addSceneAssociation(table_name,target_id, scene_id):

	# table_name: e.g. 'tag', 'star'
	# table:  SceneTag, SceneStar ORM objects

    table = getattr(models, 'Scene'+table_name.capitalize())
    col = table_name.lower()+'_id' 
    existing = session.query(table).filter(table.scene_id == scene_id, table.col == target_id) .first()
    if not existing:
	newrec = table(scene_id, target_id, tentative=True)
	session.add(newrec)
	session.flush()
	addImplied(table_name, target_id, scene_id)
    else:
	logger.debug("existing tag for scene %d target %d (of %s)" % (scene_id, target_id, table_name))



def addImplied(table_name,target_id, scene_id):
    col = table_name.lower()+'_id' 
    table = getattr(models, base_name.capitalize())
    implics = session.query(FacetImplic).filter(FacetImplic.predicate == target_id \
	, FacetImplic.predicate_type == table_name).all()
    for i in implics:
	addSceneAssociation(i.target_type, i.target, scene_id)


def permute(string):
    ret = []
    ret.append(string)
    ret.append(re.sub(r'\s','',string))   # remove spaces
    ret.append(re.sub(r'\W',' ',string))  # change non-alphanums to space (to cause splitting)

    return ret
    



#### make scenes if needed

# collect files that have no scene
for file in session.query(File).filter(not_(exists().where(SceneFile.file_id == File.id))).yield_per(200):

    # make scene if none
    scene = Scene(file.display_name)
    session.add(scene)
    session.flush()
    sf = SceneFile(scene.id, file.id)
    session.add(sf)
    session.flush()
    
session.commit()




#### collect the scenes and tag them

aliases = session.query(Alias).filter(Alias.active == True).all()

scenes = session.query(Scene).filter(Scene.confirmed != True).all()
for scene in scenes:
    agg_wordbag = session.query(func.get_words_for_scene(scene.id)).first()[0].strip()
    if not agg_wordbag:
	logger.debug("EMPTY get_words_for_scene on scene.id %d" % scene.id)
	continue
    mulched_wordbag = mulch(agg_wordbag)

    # iterate over aliases
    for a in aliases:

	# for each potential target of the alias
	for tb in ['AliasTag', 'AliasStar', 'AliasLabel', 'AliasSeries']:
	    table = getattr(models,tb)    # requires import models, not from models import...

	    # get the potential targets for this alias
	    targets = session.query(table).filter(table.alias_id == a.id).all()
	    if not targets:
		continue


	    # generate list of permutations
	    cond_list = permute(a.name)


	    # test each condition
	    for cond in cond_list:

		# other ways used to exist here for deleted alias_rule table.  instead we're now just permuting
		# the various aliases, but it might be nice to add a way to use regexs in a rule (or tsvector) in
		# the future

		match = wordmatch(a.condition, mulched_wordbag)
		

		# not > and > or
		if match and not a.exclude   or    not match and a.exclude:
		    # add the association between the target and the scene
		    for t in targets:  
			# need to lookup the tag/star/label/series id from the Alias* table+'_id'
			base = re.sub('^Alias', '', tb)
			target_id = getattr(t, base.lower()+'_id')
			addSceneAssociation(base,target_id, scene.id)

		    # we've matched this variation of the condition for this alias, let's stop
		    break


			
# session.commit()
