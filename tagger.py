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
import shlex
from itertools import tee, izip




# globals
logfile = 'logs/log.txt'


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
def tokenize(mystring):
    return ['"{0}"'.format(fragment) if ' ' in fragment else fragment for fragment in shlex.split(mystring)]

# return match if single or double-enclosed quote phrase detected
def isQuoteEnclosed(mystring):
    return re.search(r'(["\'])(?:(?=(\\?))\2.)*?\1',mystring)

# iterate pairwise through a list  "s -> (s0,s1), (s1,s2), (s2, s3), ..."
def pairwise(iterable):
	a, b = tee(iterable)
	next(b, None)
	return izip(a, b)

# break a string down into words (alphanum) and ignore quotes and all other non-alphas
def mulch(mystring):
    return re.findall(r'\w+',mystring)

# if small is a subsequence of big, returns (start, end+1) of sequence occurence
def contains(small, big):
    for i in xrange(len(big)-len(small)+1):
	for j in xrange(len(small)):
	    if type(big[i+j]) == type('') == type(small[j]):  # not typo, python allows chained ==
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
    if contains(mulch(condition),mulched_wordbag):
	return True
    return False
		
		

# add association  to  table (SceneTag, SceneStar, etc)'s target id and the scene

def addSceneAssociation(table_name,target_id, scene):

	# table_name: e.g. 'tag', 'star'
	

    # set the field on scene for label and series since they're n:1
    if table_name in ['label','series']:
	if not getattr(scene, table_name+'_id'):
	    setattr(scene,table_name+'_id', target_id)
	    session.flush()
	
    # add links in mapping tables for star adn tag
    else:
	table = getattr(models, 'Scene'+table_name.capitalize())   # table:  SceneTag, SceneStar ORM objects
	col = table_name.lower()+'_id' 
	existing = session.query(table).filter(table.scene_id == scene.id, getattr(table,col) == target_id) .first()
	if not existing:
	    newrec = table(scene.id, target_id, tentative=True)  # table:  SceneTag, SceneStar ORM objects
	    session.add(newrec)
	    session.flush()
	    logger.debug("\nAdding scene-%s association: scene_id %d %s_id %d" \
		% (table_name,scene.id,table_name,target_id))
	    addImplied(table_name, target_id, scene)
	else:
	    logger.debug("existing tag for scene %d target %d (of %s)" % (scene.id, target_id, table_name))
	    addImplied(table_name, target_id, scene)



def addImplied(table_name,target_id, scene):
    col = table_name.lower()+'_id' 
    table = getattr(models, table_name.capitalize())
    implics = session.query(FacetImplic).filter(FacetImplic.predicate == target_id \
	, FacetImplic.predicate_type == table_name).all()
    for i in implics:
	logger.debug("  add by implication")
	addSceneAssociation(i.target_type, i.target, scene)


def permute(string):
    ret = []
    ret.append(string)
    ret.append(re.sub(r'\s','',string))   # remove spaces
    ret.append(re.sub(r'\W',' ',string))  # change non-alphanums to space (to cause splitting)
    ret.append(re.sub(r'\W','',string))  # change non-alphanums to nothing
    return set(ret)  # uniques the list
    




def getAliasesAndDict():
    aliases = session.query(Alias).filter(Alias.active == True).all()
    apdict = {}
    for a in aliases:
	apdict[a.name] = permute(a.name)
    return (aliases,apdict)

    
def getTbls():
    tbls = session.query(AliasTag, AliasStar,AliasSeries,AliasLabel) \
    .select_from(Alias)\
    .outerjoin(AliasTag, AliasTag.alias_id == Alias.id) \
    .outerjoin(AliasStar, AliasStar.alias_id == Alias.id) \
    .outerjoin(AliasSeries, AliasSeries.alias_id == Alias.id) \
    .outerjoin(AliasLabel, AliasLabel.alias_id == Alias.id) \
    .all()
    
    tbls = [filter(None,r) for r in tbls]		    # remove none elements
    tbls = [item for sublist in tbls for item in sublist]   # flatten remaining list

    return tbls


########################################################################
# 
#  makeFacts(scene, [apdict, aliases, tbls]
# 
#  from crawler, can apply aliases and implications to a scene
# 
#  from tagger itself, can accept pre-built list of Alias, fully joined 
#        tbls, and pre-permuted alias conditions in apdict to seriously 
#        increase speed
# 
########################################################################




def makeFacets(scene, apdict=None, aliases=None, tbls=None):

    if not apdict or not aliases: # not > or
	(aliases, apdict) = getAliasesAndDict()

    if not tbls:
	tbls = getTbls()

    agg_wordbag = session.query(func.get_words_for_scene(scene.id)).first()[0].strip().lower()
    if not agg_wordbag:
	logger.debug("EMPTY get_words_for_scene on scene.id %d" % scene.id)
	return
    mulched_wordbag = mulch(agg_wordbag)

    sys.stdout.write("S")
    sys.stdout.flush()

    # iterate over aliases
    for a in aliases:


	#sys.stdout.write("A")
	#sys.stdout.flush()

	# test each condition
	for cond in apdict[a.name]:

	    # other ways used to exist here for deleted alias_rule table.  instead we're now just permuting
	    # the various aliases, but it might be nice to add a way to use regexs in a rule (or tsvector) in
	    # the future

	    match = wordmatch(cond, mulched_wordbag)

	    # not > and > or
	    if match:
		for t in [r for r in tbls if r.alias_id == a.id]:   # e.g. AliasTag object
		# add the association between the target and the scene
		    base = re.sub('^Alias', '', t.__class__.__name__).lower()
		    target_id = getattr(t, base.lower()+'_id')
		    addSceneAssociation(base,target_id, scene)

		# we've matched this variation of the condition for this alias, let's stop
		continue

	



#### prepare some data to speed things up, including permuted aliases, and alias-* association tables

if __name__ == '__main__':



    #### make scenes if needed
    # collect files that have no scene
    for file in session.query(File).filter(not_(exists().where(SceneFile.file_id == File.id))).yield_per(200):

	# make scene if none
	scene = Scene(file.display_name)
	m = re.findall(r'^&+|&+$|(?<=\W)&+(?=\W)',file.display_name)
	scene.rating = len(max(m,key=len)) if m else 0
	session.add(scene)
	session.flush()
	sf = SceneFile(scene.id, file.id)
	session.add(sf)
	session.flush()
	    
    session.commit()



    (aliases, apdict) = getAliasesAndDict()

    # get the tables
    tbls = getTbls()

    scenes = session.query(Scene).filter(Scene.confirmed != True).all()
    for scene in scenes:
	makeFacets(scene, aliases=aliases, apdict=apdict, tbls=tbls)



    session.commit()



