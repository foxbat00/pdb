#!/usr/bin/env python
from sqlalchemy import *
import sqlalchemy.dialects as postgres
from sqlalchemy.orm import scoped_session, sessionmaker
import datetime
import dateutil.parser as dup
import re, sys, os
import hashlib
import logging, threading, Queue


# globals
logfile = 'logs/log.txt'
validExts = [".rm", ".avi", ".mpeg", ".mpg", ".divx", ".vob", ".wmv", ".ivx", ".3ivx", ".m4v", ".mkv"]
threadMax = 4


# threading queues
fileq = Queue.Queue()
repoq = Queue.Queue()

# set up db
from db import *

# logging
logging.basicConfig(level=logging.DEBUG, format="%(threadName)s:%(thread)d:  %(message)s")
logger = logging.getLogger(__name__)



logger.info("##### starting new file crawl at %s" % datetime.datetime.now())


#############################################################
#
#   functions
#
#############################################################


# avoid '.' winding up in assembled paths
def modJoin(*paths):
    return os.path.join(*[x for x in paths if x != '.'])



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

    # repo is an ORM object, path and fname are strings

def considerFile(scanfile):

    repo, path, fname = scanfile.dump()
    
    fpart,ext = os.path.splitext(fname)
    fullname = modJoin(repo.path,path,fname)
    fsize = os.path.getsize(fullname)

    logger.debug("considering %s" % fullname)


    if not validExt(ext):
	logger.debug("   not valid extension")
	return

    # shortcut - if this file matches by filename and size, let's avoid md5summing it.
    f,fi = session.query(File, FileInst).filter(File.size == fsize, FileInst.name == fname\
	, FileInst.path == path, FileInst.repository == repo.id).first()
    if f and fi:
	logger.debug(" shortcutting")
	f.last_crawled = datetime.datetime.now()  # consider this later
	fi.last_seen = datetime.datetime.now()
	fi.deleted_on = None
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
	return
    
    else:
	
	# mark as crawled
	f.last_crawled = datetime.datetime.now()
	session.add(f)
	session.commit()

	# get corresponding file_insts
	fis = session.query(FileInst,Repository).join(Repository).filter(FileInst.file == existing.id).all()
	logger.debug("   found file and %d existing instances" % int(len(fis)/2) )


	# scan for deleted, mark as seen the rest
	for fi,r in fis:
	    updateFileInst(fi,r)
	    

	# if an instance has been deleted recently, let's reactivate it 
	for fi,r in fis:
	    d = fi.deleted_on
	    if d and d > datetime.datetime.now() - datetime.timedelta(weeks=1):
		logdebug("      reactivating old instance")
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
		logger.debug("      creating new instance")
		fi = FileInst(fname,path,repo,existing)
		session.add(fi)
		session.commit()
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



class FileLoader(threading.Thread):

    def __init__(self,repoq,fileq):
	threading.Thread.__init__(self)
	self.repoq = repoq
	self.fileq = fileq

    def scanErro(e):
	raise e

    def addFile(self,sf):
	#session.expunge(r)
	logger.debug("adding %s to fileq" % sf)
	self.fileq.put(sf)

    # not used but could enable limiting recursive crawl to particular depth

    def run(self):
	#while not self.repoq.empty():
	while True:
	    r = self.repoq.get()
	    #session.merge(r, load=False)
	    logger.debug("Examining repo: %s" % r)
	    
	    if not os.path.isdir(r.path):
		logger.error("Repository not found: %s" % r.path)
		break
	    walkargs = {'followlinks':True, 'onerror':'self.scanError'}
	    # recurse
	    for dirpath, dirname, files in os.walk(r.path,**walkargs):
		for f in files:
		    sf = ScanFile(r,os.path.relpath(dirpath,r.path),f)
		    self.addFile(sf)
	    self.repoq.task_done()
	    
    """
    def walklevel(dir, level=1, walkargs=None):
	dir = dir.rstrip(os.path.sep)
	num_sep = dir.count(os.path.sep)
	for root,dirs,files in os.walk(dir,**walkargs):
	    yield root, dirs, files
	    num_sep_this = root.count(os.path.sep)
	    if num_sep + level <=num_sep_this:
		del dirs[:]
    """




class FileScanner(threading.Thread):
    
    def __init__(self,fileq):
	threading.Thread.__init__(self)
	self.fileq = fileq


    def run(self):
	logger.debug("fileScanner running")
	#while not self.fileq.empty():
	while True:
	    sf = self.fileq.get()
	    session.merge(r,load = False)
	    considerFile(sf)
	    self.fileq.task_done()




class FileUpdater(threading.Thread):
    
    def __init__(self,fileq):
	threading.Thread.__init__(self)
	self.fileq = fileq


    def run(self):
	while not self.fileq.empty():
	    (fi,r) = self.fileq.get()
	    session.merge(fi, load=False)
	    session.merge(r, load = False)
	    logger.debug("updating %s" % modJoin(r.path,fi.path,fi.name))
	    updateFileInst(fi,r)
	    self.fileq.task_done()






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
    t = FileLoader(repoq,fileq)
    t.daemon = True  # the prog ends when no alive non-daemons are left
    t.start()

logger.debug("adding files to queue")

for r in rs:
    logger.debug("enqueuing repository %s" % r)
    repoq.put(r)

repoq.join() # wait/ensure for everything to be added...
# ideally, I'd like to start consuming before I'm done producing, but not sure how without risking queue emptiness
# and or having to manually signal the end

logger.debug(" %d files in fileq" % fileq.qsize())
logger.debug("beginning threaded scan of files")

for i in range (threadMax):
    t  = FileScanner(fileq)
    t.daemon = True  # the prog ends when no alive non-daemons are left
    t.start()

fileq.join()



logger.debug("###### crawl for new files -- complete %s #######" % datetime.datetime.now())

# check file_instances that we haven't seen in a while
for fi,r in session.query(FileInst,Repository).join(Repository).filter(FileInst.deleted_on == None)\
	.filter(FileInst.last_seen < datetime.datetime.now() - datetime.timedelta(days=3)).yield_per(300):
    session.expunge(fi)
    session.expunge(r)
    fileq.put( (fi,r) )


for i in range (threadMax):
    t = FileUpdater(fileq)
    t.start()

fileq.join()

logger.debug("###### crawl of files not recently seen -- complete %s #######" % datetime.datetime.now())


session.close()



