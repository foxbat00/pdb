#!/usr/bin/env python
from sqlalchemy import *
import sqlalchemy.dialects as postgres
from sqlalchemy.orm import scoped_session, sessionmaker
import datetime
import re, sys, os
import argparse
from db import *
from models import *



validExts = [".rm", ".avi", ".mpeg", ".mpg", ".divx", ".vob", ".wmv", ".ivx", ".3ivx"
     , ".m4v", ".mkv", ".mov", ".asf", ".mp4", ".flv", ".3gp",".asf", ".divx" ]


# options parsing
parser = argparse.ArgumentParser(description='PDB file-extension surveyor')

parser.add_argument('-x','--exclude', nargs='+', type=int, help='repositories to exclude from crawl, by id')
args = parser.parse_args()

excludeRepos = []
if args.exclude:
    for r in args.exclude:
	excludeRepos.append(r)

session = scoped_session(sessionmaker(autocommit=False, autoflush=True, bind=engine))


def scanError(e):
    raise e

tokendict = {}
rs = session.query(Repository).all()

for r in rs:
    if r in excludeRepos:
	continue

    print "surveying repo: %s" % r
    rpath = r.path

    if not os.path.isdir(rpath):
	print "Repository not found: %s" % rpath
	continue

    walkargs = {'followlinks':True, 'onerror':'self.scanError'}
    # recurse
    for root, dirs, files in os.walk(rpath,**walkargs):
	for f in files:
	    fpart,ext = os.path.splitext(f)
	    tokens = re.findall(r'[A-Za-z]+',fpart)
	    for t in tokens:
		if t.lower() in tokendict:
		    tokendict[t.lower()] += 1
		else:
		    tokendict[t.lower()] = 1
		continue

for v,k in sorted( ((v,k) for k,v in tokendict.iteritems()), reverse=True):
    print "%s:  %d" % (k, v)


