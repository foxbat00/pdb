#!/usr/bin/env python
from sqlalchemy import *
import sqlalchemy.dialects as postgres
import sqlalchemy.orm as orm
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import datetime
import re
import sys, os
import dateutil.parser as dup



from db import *

# enable control of recursive crawl
def walklevel(dir, level=1, walkargs=None):
    dir = dir.rstrip(os.path.sep)
    num_sep = dir.count(os.path.sep)
    for root,dirs,files in os.walk(dir,**walkargs):
	yield root, dirs, files
	num_sep_this = root.count(os.path.sep)
	if num_sep + level <=num_sep_this:
	    del dirs[:]


def validExt(ext):
    return True if ext.lower() in validExts else False

def md5sum(file):
    md5 = hashlib.md5()
    with open(file,'rb') as f:
	for chunk in iter(lambda: f.read(128*md5.block_size),b''):
	    md5.update(chunk)
    return md5.hexdigest()


def updateFileInst(fi,r):
    if not os.path.isfile(os.path.join(r.path,fi.path,fi.name)):
	fi.deleted_on = datetime.datetime.now()
    else:
	fi.last_seen = datetime.datetime.now()
    session.add(fi)
    session.commit(fi)
    return fi,r


os.environ['PYTHONINSPECT'] = 'True'
