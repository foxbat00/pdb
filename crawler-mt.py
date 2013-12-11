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


# globals
logfile = 'logs/log.txt'
validExts = [".rm", ".avi", ".mpeg", ".mpg", ".divx", ".vob", ".wmv", ".ivx", ".3ivx", ".m4v", ".mkv"]
threadMax = 4


# threading queues
fileq = Queue()
repoq = Queue()

# set up db
from db import *
from models import *
from util import *

# logging
format = "%(levelname)s (%(threadName)s): %(message)s"
logging.basicConfig(level=logging.DEBUG, format=format)
logger = logging.getLogger(__name__)
logoutput = logging.FileHandler(logfile, mode='w')
logoutput.setLevel(logging.DEBUG)
logoutput.setFormatter(logging.Formatter(format))
logger.addHandler(logoutput)

#logger.setLevel(logging.INFO)



logger.info("##### starting new file crawl at %s" % datetime.datetime.now())


#############################################################
#
#   functions
#
#############################################################

def validExt(ext):
    return True if ext.lower() in validExts else False

def updateFileInst(fi,r):
    if not os.path.isfile(modJoin(r.path,fi.path,fi.name)):
	fi.deleted_on = datetime.datetime.now()
    else:
	fi.last_seen = datetime.datetime.now()
    session.commit()
    return fi,r



# consider a particular file

    # repo is an ORM object, path and fname are strings

def considerFile(scanfile):

    repo, path, fname = scanfile.dump()
    
    fullname = modJoin(repo.path,path,fname)
    fsize = os.path.getsize(fullname)

    logger.info("considering %s" % fullname)


    # shortcut - if this file matches by filename and size, let's avoid md5summing it.
    q = (session.query(FileInst,File).join(File).filter(File.size == fsize, FileInst.name == fname \
	, FileInst.path == path, FileInst.repository == repo.id).first() )
    if q:
	(fi,f) = q
	logger.debug(" shortcutting")
	f.last_crawled = datetime.datetime.now()  # consider this later
	fi.last_seen = datetime.datetime.now()
	fi.deleted_on = None
	session.commit()
	session.expunge(f)
	session.expunge(fi)
	return


    logger.debug (" checksumming...")
    fhash = md5sum(fullname)

    # see if the size matches any recorded file
    existing = session.query(File).filter(File.size==fsize).filter(File.md5hash==fhash).first()

    if not existing:
	
	logger.debug("   no existing file matches")

	f = File(fsize,fhash,fname)
	fi = FileInst(fname, path, repo, f)
	session.add(f)
	session.add(fi)
	session.commit()
	session.expunge(f)
	session.expunge(fi)
	return
    
    else:
	
	# mark as crawled
	existing.last_crawled = datetime.datetime.now()
	session.commit()

	# get corresponding file_insts
	q = session.query(FileInst,Repository).join(Repository).filter(FileInst.file == existing.id).all()
	logger.debug("   found file and %d existing instances" % int(len(fis)/2) )


	# scan for deleted, mark as seen the rest
	for q in fis:
	    (fi,r) = q
	    updateFileInst(fi,r)
	    

	# if an instance has been deleted recently, let's reactivate it 
	for q in fis:
	    (fi,r) = q
	    d = fi.deleted_on
	    if d and d > datetime.datetime.now() - datetime.timedelta(weeks=1):
		logdebug("      reactivating old instance")
		fi,r = fis
		fi.name = fname
		fi.path = path
		fi.repository = repo.id
		fi.last_seen = datetime.datetime.now()
		deleted_on = None
		session.commit()
		session.expunge(fi)
		session.expunge(existing)
		return

	# otherwise, create a new file instance
	    else:
		logger.debug("      creating new instance")
		fi = FileInst(fname,path,repo,existing)
		session.add(fi)
		session.commit()
		session.expunge(fi)
		return
		    
			
#############################################################
#
#  thread classes
#
#############################################################


class ScanFile():
    def __init__(self,repo,relpath,fname):
	self.repo = repo
	self.relpath = relpath
	self.fname = fname
    def __repr__(self):
	return "<ScanFile repo=%d, relpath=%s, fname=%s>" % (self.repo.id, self.relpath, self.fname)
    def dump(self):
	return self.repo,self.relpath,self.fname







def FileLoader(repoq,fileq):

    def scanErro(e):
	raise e

    logger.debug("fileLoader running")
    #while not self.repoq.empty():
    while True:
	r = repoq.get()
	#session.merge(r, load=False) # not needed bc this comes from main thread???
	logger.info("Examining repo: %s" % r)
	
	if not os.path.isdir(r.path):
	    logger.error("Repository not found: %s" % r.path)
	    break
	walkargs = {'followlinks':True, 'onerror':'self.scanError'}
	# recurse
	for dirpath, dirname, files in os.walk(r.path,**walkargs):
	    for f in files:
		fpart,ext = os.path.splitext(f)
		if not validExt(ext):
		    logger.debug("   not valid extension")
		    break
		sf = ScanFile(r,os.path.relpath(dirpath,r.path),f)
		logger.debug("adding %s to fileq" % sf)
		fileq.put(sf)
	repoq.task_done()
	    


def FileScanner (fileq):
	logger.debug("fileScanner running")
	#while not self.fileq.empty():
	while True:
	    sf = fileq.get()
	    session.merge(r,load = False)
	    considerFile(sf)
	    fileq.task_done()




def FileUpdater(fileq):
    logger.debug("fileUpdater running")
    while True:
	(fi,r) = fileq.get()
	session.merge(fi, load=False)
	session.merge(r, load = False)
	logger.debug("updating %s" % modJoin(r.path,fi.path,fi.name))
	updateFileInst(fi,r)
	fileq.task_done()






#############################################################
#
#  main
#
#############################################################

# load repositories
rs = session.query(Repository).all()


# walk the files in each repository


logger.debug("launching FileLoaders")

for i in range (threadMax if len(rs) > threadMax else len(rs)):
    t = Thread(target=FileLoader, args=(repoq,fileq))
    t.daemon = True  # the prog ends when no alive non-daemons are left
    t.start()


for r in rs:
    logger.debug("enqueuing repository %s" % r)
    repoq.put(r)

for i in range (threadMax):
    t  = Thread(target=FileScanner, args=(fileq,)) # requires a tuple
    t.daemon = True  # the prog ends when no alive non-daemons are left
    t.start()

fileq.join()
logger.info(" --done loadine files    -- complete %s" % datetime.datetime.now())
repoq.join() # wait/ensure for everything to be added...
logger.info(" --done scanning files    -- complete %s" % datetime.datetime.now())



logger.info("###### crawl for new files -- complete %s #######" % datetime.datetime.now())

# check file_instances that we haven't seen in a while
for q in session.query(FileInst,Repository).join(Repository).filter(FileInst.deleted_on == None)\
	.filter(FileInst.last_seen < datetime.datetime.now() - datetime.timedelta(days=3)).yield_per(300):
    (fi,r) = q
    session.expunge(fi)
    session.expunge(r)
    fileq.put(q)


for i in range (threadMax):
    t = Thread(target=FileUpdater,args=(fileq,))  # requires a tuple
    t.daemon = True  # the prog ends when no alive non-daemons are left
    t.start()

fileq.join()
logger.info("###### crawl of files not recently seen -- complete %s #######" % datetime.datetime.now())


session.close()



