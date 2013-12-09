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
import hashlib




#################################################################
#
# No longer being developed - see multithreaded crawler
#
#################################################################




# 
logfile = 'logs/log.txt'
validExts = [".rm", ".avi", ".mpeg", ".mpg", ".divx", ".vob", ".wmv", ".ivx", ".3ivx", ".m4v", ".mkv"]
bDebug= True


from db import *

# open log file
logf = open(logfile,'w')
def log(msg):
    print msg
    logf.write("%s\n" % msg)


log("##### starting new file crawl at %s" % datetime.datetime.now())


# avoid '.' winding up in assembled paths
def modJoin(*paths):
    return os.path.join(*[x for x in paths if x != '.'])


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
    if not os.path.isfile(modJoin(r.path,fi.path,fi.name)):
	fi.deleted_on = datetime.datetime.now()
    else:
	fi.last_seen = datetime.datetime.now()
    session.add(fi)
    session.commit()
    return fi,r



# consider a particular file

def considerFile(repo,path,fname):

    fpart,ext = os.path.splitext(fname)
    fullname = modJoin(repo.path,path,fname)
    fsize = os.path.getsize(fullname)

    if bDebug:
	log("consider %s" % fullname)


    if not validExt(ext):
	log("   not valid extension")
	return

    # shortcut - if this file matches by filename and size, let's avoid md5summing it.
    f,fi = session.query(File, FileInst).filter(File.size == fsize, FileInst.name == fname\
	, FileInst.path == path, FileInst.repository == repo.id).first()
    if f and fi:
	log(" shortcutting")
	f.last_crawled = datetime.datetime.now()
	fi.last_seen = datetime.datetime.now()
	fi.deleted_on = None
	return

    
	

    log (" checksumming...")
    fhash = md5sum(fullname)

    # see if the size matches any recorded file
    existing = session.query(File).filter(File.size==fsize).filter(File.md5hash==fhash).first()

    if not existing:
	
	if bDebug:
	    log("   no existing file matches")

	f = File(fsize,fhash,fname)
	fi = FileInst(fname, path, repo, f)
	session.add(f)
	session.add(fi)

	session.commit()
	return
    
    else:
	
	# mark as crawled
	f.last_crawled = datetime.datetime.now()
	session.add(f)
	session.commit()

	# get corresponding file_insts
	fis = session.query(FileInst,Repository).join(Repository).filter(FileInst.file == existing.id).all()
	if bDebug:
	    log("   found file and %d existing instances" % int(len(fis)/2) )


	# scan for deleted, mark as seen the rest
	for fi,r in fis:
	    updateFileInst(fi,r)
	    

	# if an instance has been deleted recently, let's reactivate it 
	for fi,r in fis:
	    d = fi.deleted_on
	    if d and d > datetime.datetime.now() - datetime.timedelta(weeks=1):
		if bDebug:
		    log("      reactivating old instance")
		fi,r = fis
		fi.name = fname
		fi.path = path
		fi.repository = repo.id
		last_seen = datetime.datetime.now()
		deleted_on = None
		session.add(fi)
		session.commit(fi)
		return

	# otherwise, create a new file instance
	    else:
		if bDebug:
		    log("      creating new instance")
		fi = FileInst(fname,path,repo,existing)
		session.add(fi)
		session.commit()
		return
		    
			


def scanErro(e):
    raise e

# load repositories
rs = session.query(Repository).all()


# walk the files in each repository
for r in rs:
    if not os.path.isdir(r.path):
	log("Repository not found: %s" % r.path)
	break
    walkargs = {'followlinks':True, 'onerror':'self.scanError'}
    # recurse
    for dirpath, dirname, files in os.walk(r.path,**walkargs):
	for f in files:
	    considerFile(r,os.path.relpath(dirpath,r.path),f)





log("###### crawl for new files -- complete %s #######" % datetime.datetime.now())

# check file_instances that we haven't seen in a while
others = session.query(FileInst,Repository).join(Repository).filter(FileInst.deleted_on == None)\
    .filter(FileInst.last_seen < datetime.datetime.now() - datetime.timedelta(days=3)).all()
for fi,r in others:
    log("updating %s" % modJoin(r.path,fi.path,fi.name))
    updateFileInst(fi,r)
log("###### crawl of files not recently seen -- complete %s #######" % datetime.datetime.now())





session.close()
#os.environ['PYTHONINSPECT'] = 'True'
