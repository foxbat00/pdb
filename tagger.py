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
import argparse




# globals
logfile = 'logs/log.txt'


# set up db
from db import *
from models import *
import models # needed for getattr magic
from helpers import *

# logging
format = "%(levelname)s (%(threadName)s): %(message)s"
logging.basicConfig(level=logging.DEBUG, format=format)
logger = logging.getLogger(__name__)
logoutput = logging.FileHandler(logfile, mode='w')
logoutput.setLevel(logging.DEBUG)
logoutput.setFormatter(logging.Formatter(format))
logger.addHandler(logoutput)

#logger.setLevel(logging.INFO)





# add association  to  table (SceneTag, SceneStar, etc)'s target id and the scene

def addSceneAssociation(session, table_name,target_id, scene):

	# table_name: e.g. 'tag', 'star'
	
    def getTargetName(table_name, target_id):
	t = getattr(models, table_name.capitalize())
	return session.query(t).filter(t.id == target_id).first()

    def addImplied(table_name,target_id, scene):
	col = table_name.lower()+'_id' 
	table = getattr(models, table_name.capitalize())
	implics = session.query(FacetImplic).filter(FacetImplic.predicate == target_id \
	    , FacetImplic.predicate_type == table_name).all()
	for i in implics:
	    logger.debug("  add by implication: #%s# scene %d target %d %s" \
		% (i,scene.id,target_id,getTargetName(table_name,target_id)))
	    addSceneAssociation(session, i.target_type, i.target, scene)


    # set the field on scene for label and series since they're n:1
    if table_name in ['label','series']:
	if not getattr(scene, table_name+'_id'):
	    setattr(scene,table_name+'_id', target_id)
	    session.flush()
	
    # add links in mapping tables for star and tag
    else:
	table = getattr(models, 'Scene'+table_name.capitalize())   # table:  SceneTag, SceneStar ORM objects
	col = table_name.lower()+'_id' 
	existing = session.query(table).filter(table.scene_id == scene.id, getattr(table,col) == target_id).first()
	if not existing:
	    newrec = table(scene.id, target_id, tentative=True)  # table:  SceneTag, SceneStar ORM objects
	    session.add(newrec)
	    session.flush()
	    logger.debug("\nAdding scene-%s association: scene_id %s %s_id %s %s " \
		% (table_name,scene.id,table_name,target_id, getTargetName(table_name,target_id)))
	    addImplied(table_name, target_id, scene)
	else:
	    logger.debug("existing tag for scene %s target %s %s (of %s)" \
		% (scene.id, target_id, getTargetName(table_name, target_id), table_name))
	    addImplied(table_name, target_id, scene)




def permute(string):
    ret = []
    ret.append(string)
    ret.append(re.sub(r'\s','',string))   # remove spaces
    ret.append(re.sub(r'\W',' ',string))  # change non-alphanums to space (to cause splitting)
    ret.append(re.sub(r'\W','',string))  # change non-alphanums to nothing
    return set(ret)  # uniques the list
    



# see below, but these are for pre-pulling a lot of the expensive data the tagger needs regularly


def getAliasesAndDict(session):
    aliases = session.query(Alias).filter(Alias.active == True).all()
    apdict = {}
    for a in aliases:
	apdict[a.name] = permute(a.name)
    return (aliases,apdict)

    
def getTbls(session):
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
#  makeFacts(session, scene, [apdict, aliases, tbls]
# 
#  from crawler, can apply aliases and implications to a scene
# 
#  from tagger itself, can accept pre-built list of Alias, fully joined 
#        tbls, and pre-permuted alias conditions in apdict to seriously 
#        increase speed
# 
########################################################################




def makeFacets(session, scene, apdict=None, aliases=None, tbls=None):

    if not scene:
	logger.debug("scene passed to makeFacets is null!!!!")
	return


    # skip if scene is locked
    if scene.confirmed:
	return



    if not apdict or not aliases: # not > or
	(aliases, apdict) = getAliasesAndDict(session)

    if not tbls:
	tbls = getTbls(session)

    #agg_wordbag = session.query(func.get_words_for_scene(scene.id)).first()[0]
    agg_wordbag = scene.wordbag
    agg_wordbag = agg_wordbag.strip().lower()
    if not agg_wordbag:
	logger.debug("EMPTY get_words_for_scene on scene.id %d" % scene.id)
	return
    mulched_wordbag = mulch(agg_wordbag)

    #sys.stdout.write("S")
    #sys.stdout.flush()

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
		    addSceneAssociation(session, base,target_id, scene)

		# we've matched this variation of the condition for this alias, let's stop
		continue

    session.commit()
    session.expunge_all()
    return

	



#### prepare some data to speed things up, including permuted aliases, and alias-* association tables

if __name__ == '__main__':

    session = scoped_session(sessionmaker(autocommit=False, autoflush=True, bind=engine))

    # options parsing
    # ARGPARSE argparse
    parser = argparse.ArgumentParser(description='PDB tagger')

    parser.add_argument('--make_scenes',  action='store_true', \
	help='Make scenes for any files without an entry in scene_file before tagging')
		
    args = parser.parse_args()


    if(args.make_scenes):
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



    (aliases, apdict) = getAliasesAndDict(session)

    # get the tables
    tbls = getTbls(session)

    scenes = session.query(Scene).filter(Scene.confirmed != True).all()
    for scene in scenes:
	makeFacets(session, scene, aliases=aliases, apdict=apdict, tbls=tbls)



    session.commit()




