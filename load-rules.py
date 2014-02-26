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
import argparse
import string


#### does not touch scenes, only tags, stars, labels, series, facet_implications, aliases and mapping tables


# set up db
from db import *
from models import *
import models # needed for getattr magic
from util import *

if __name__ == '__main__':
    # globals
    logfile = 'logs/log.txt'

    session = scoped_session(sessionmaker(autocommit=False, autoflush=True, bind=engine))

    # logging
    format = "%(levelname)s (%(threadName)s): %(message)s"
    logging.basicConfig(level=logging.DEBUG, format=format)
    logger = logging.getLogger(__name__)
    logoutput = logging.FileHandler(logfile, mode='w')
    logoutput.setLevel(logging.DEBUG)
    logoutput.setFormatter(logging.Formatter(format))
    logger.addHandler(logoutput)

    # options parsing
    parser = argparse.ArgumentParser(description='PDB crawler')
    parser.add_argument('-f', type=str, required=True, help='File to load from')
    parser.add_argument('-s', '--dryrun',action='store_true', default=False,  help='Load rules to check formating but do no touch the DB')
    args = parser.parse_args()
    loadfile = args.f
    simulate = args.dryrun if args.dryrun else None
    if not loadfile:
	logger.debug("No loadfile")
    if not os.path.isfile(loadfile):
	logger.debug("loadfile not found: %s" % loadfile)



    # strip enclosing spaces and quotes
    def mystrip(mystring):
	return mystring.strip().strip('\'"').strip()

    # break a string down into words and quote-enclosed phrases
    def tokenize(mystring):
	return ['"{0}"'.format(fragment) if ' ' in fragment else fragment for fragment in shlex.split(mystring)]

    # return match if single or double-enclosed quote phrase detected
    def isQuoteEnclosed(mystring):
	return re.search(r'(["\'])(?:(?=(\\?))\2.)*?\1',mystring)

    # break a string down into words (alphanum) and ignore quotes and all other non-alphas
    def mulch(mystring):
	return re.findall(r'\w+',mystring)

    # iterate pairwise through a list  "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    def pairwise(iterable):
	    a, b = tee(iterable)
	    next(b, None)
	    return izip(a, b)

    # if small is a subsequence of big, returns (start, end+1) of sequence occurence
    def contains(small, big):
	for i in xrange(len(big)-len(small)+1):
	    for j in xrange(len(small)):
		if big[i+j] != small[j]:
		    break
	    else:
		return i, i+len(small)
	return False



    with open(loadfile, 'rU') as lf:
	linei=0
	for line in lf.readlines():
	    linei+=linei

	    # elimiate comments
	    line = re.sub(r'#.*$','',line)
	    # if empty, skip
	    if re.search(r'^\s+$',line):
		continue

	    mo = re.match(r'^\s*(\w+)\s+((["\'])(?:(?=(\\?))\4.)*?\3|(([^\]]+)))\s+\[\s*([^\]]*)\s*\]\s+\[\s*([^\]]*)\s*\]\s*$', line)
	    if not mo or len( mo.groups() ) < 4:
		logger.debug("MALFORMED RULE line %d: %s" % (linei,line))
		sys.exit()


	    facet_type = mo.group(1)
	    name = mo.group(2)
	    implic = mo.group(7)
	    aliases = mo.group(8)
	    
	    # remove enclosing quotes, extra space
	    name = mystrip(name)

		
	    #clean up implic
	    implic_dct = None
	    if implic != '':
		implic_dct = {}
		lst = re.split(',',implic)
		for i in range(len(lst)):
		    try:
			(facet,val) = re.split(':',lst[i]) 
		    except ValueError:
			logger.debug("Malformed implication line %d: %s" % (linei,implic))
			sys.exit()
		    val = mystrip(val)
		    facet = mystrip(facet)
		    implic_dct[facet] = val

	    # clean up aliases
		# hack for gender on stars
	    gender = 'f'
	    if facet_type == 'star' and re.search(r'_m$',name):
		    name = re.sub(r'_m$','',name)
		    gender = 'm'
	    aliases = aliases +','+name # add the name as an alias
	    aliases = aliases.lower()
	    al = re.split(',',aliases)  # split on coma
		# remove empty strings from trailing commas
	    alias_list = [mystrip(a) for a in al if mystrip(a)]  
	    if not alias_list:
		logger.debug("ERROR - empty alias list - shouldn't happen")
		sys.exit()


	    # facet_type, name, implic_dct, alias_list
	    logger.debug("facet_type = %s, name = %s, implic_dct = %s, alias_list = %s" \
		% (facet_type, name, implic_dct, alias_list) )
	    


	    # check/create the necessary facets in case they don't exist yet

	    # thing this row describes
	    table  = getattr(models, facet_type.capitalize())
	    existing = session.query(table).filter(table.name == name).first()
	    if not existing:
		logger.debug("existing not found: %s %s" % (facet_type, name))
		existing = table(name)
		# hack for gender on stars
		if facet_type == 'star':
		    existing.gender = gender
		session.add(existing)
		session.flush()

	    # aliases
	    for a in alias_list:
		a = a.lower()
		alias = session.query(Alias).filter(Alias.name == a).first()
		if not alias:
		    logger.debug("alias not found: %s" % a)
		    alias = Alias(a)
		    session.add(alias)
		    session.flush()
		
		# linkage
		ltable = getattr(models, "Alias"+facet_type.capitalize())
		link = session.query(ltable).filter(ltable.alias_id == alias.id \
		    , getattr(ltable,facet_type+"_id") == existing.id ).first()
		if not link:
		    logger.debug("alias_%s not found for alias_id %s and %s_id %s" \
			% (facet_type, alias.id, facet_type, existing.id))
		    link = ltable(alias.id, existing.id)
		    session.add(link)
		    session.flush()


	    # NOT implied stuff!!


	    # loop for implications 
	    if implic_dct:
		for k,v in implic_dct.iteritems():
		    # k is the facet (tag); v is the facet-value (xyz)
		    v = mystrip(v)
		    k = mystrip(k)
		    itable = getattr(models, k.capitalize())
		    vlower = v.lower()
		    tar = session.query(itable).filter(func.lower(itable.name) == vlower).first()
		    if not tar:
			logger.debug('ERROR:  not recognized facet/value:  "%s:%s" on line "%s"' % (k,v, line))
			sys.exit()
		    ex = session.query(FacetImplic).filter(FacetImplic.predicate == existing.id \
			, FacetImplic.predicate_type == facet_type, FacetImplic.target == tar.id \
			, FacetImplic.target_type == k).first()
		    if not ex:
			logger.debug('no facet_implication found for %d %s => %d %s' \
			    % (existing.id, facet_type, tar.id, k))
			facet_imp = FacetImplic(existing.id, facet_type, tar.id, k)
			session.add(facet_imp)
			session.flush()

	    # the tagger does the actual work of applying the implications

    if not simulate:
	session.commit()



