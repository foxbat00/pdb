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

# options parsing
parser = argparse.ArgumentParser(description='PDB crawler')
parser.add_argument('-f', type=str, help='File to load from')
args = parser.parse_args()
loadfile = args.f
if not loadfile:
    logger.debug("No loadfile")
if not os.path.isfile(loadfile):
    logger.debug("loadfile not found: %s" loadfile)





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
            if big[i+j] != small[j]:
                break
        else:
            return i, i+len(small)
    return False




with open(loadfile, 'rU') as lf:
    for line in <lf>:
	if re.search(r'^#',line) or re.search(r'^\s+$',line):
	    continue

	mo = re.match(r'^\s*(\w+)\s+([\w-]+)\s+\[\s*([^\]]*)\s*\]\s+\[\s*([^\]]*)\s*\]\s*', str)
	res = []
	if not mo or len(mo.groups()) < 5:
	    logger.debug("MALFORMED RULE: %s" % line
	    sys.exit()


	facet_type = mo.group(1)
	name = mo.group(2)
	implic = mo.group(3)
	aliases = mo.group(4)
	
	# remove enclosing quotes
	name = name.strip('\'"')

	    
	#clean up implic
	lst = re.split(',',implic)
	implic_dct = {}
	for i in range(len(lst)):
	    (facet,val) = split(':',lst.i) 
	    val = val.strip('\'"')
	    implic_dct.append((facet,val))

	# clean up aliases
	al = re.split(',',implic)  # split on coma
	alias_list = [al for al in al if al]  # remove empty strings from trailing commas


	# facet_type, name, implic_dct, alias_list
	logger.debug("facet_type = %s, name = %s, implic_dct = %s, alias_list = %s" \
	    % (facet_type, name, implic_dct, alias_list) )


	# check/create the necessary facets in case they don't exist yet

	# thing this row describes
	table  = getattr(models, facet_type)
	existing = session.query(table).filter(table.name == name).first()
	if not existing:
	    logger.debug("existing not found: %s %s" % (facet_type, name))
	    existing = table(name)
	    session.add(existing)
	    session.flush()

	# aliases
	for a in alias_list:
	    alias = session.query(Alias).filter(Alias.name == a).first()
	    if not alias:
		logger.debug("alias not found: %s" % a)
		alias = Alias(a)
		session.add(alias)
		session.flush()
	    
	    # linkage
	    ltable = getattr(models, "Alias"+facet_type)
	    link = session.query(ltable).filter(ltable.alias_id == alias.id \
		, getattr(ltable,facet_type+"_id") == existing.id ).first()
	    if not link:
		logger.debug("alias_%s not found: %s" % (facet_type, alias.id))
		link = ltable(alias.id, existing.id)
		session.add(new)
		session.flush()


	# NOT implied stuff!!


    # loop for implications 
    for (k,v) in implic_dct:
	# k is the facet (tag); v is the facet-value (xyz)
	tar = session.query(getattr(model, k)).filter(table.name == v).first()
	if not tar:
	    logger.debug("ERROR:  not recognized:  %s:%s on line %s" % (v,k, line)
	    sys.exit()
	facet_imp = FacetImplic(existing.id, facet_type, tar.id, k)
	session.add(facet_impl)
	session.flush()

    # the tagger does the actual work of applying the implications

