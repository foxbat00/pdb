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


# globals
logfile = 'logs/log.txt'
validExts = [".rm", ".avi", ".mpeg", ".mpg", ".divx", ".vob", ".wmv", ".ivx", ".3ivx"
    , ".m4v", ".mkv", ".mov", ".asf", ".mp4", ".flv"]
invalidExts = []
threadMax = 4


# threading queues
fileq = Queue()
repoq = Queue()
updateq = Queue()

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


@contextmanager
def transaction_context():
    """Provide a transactional scope around a series of operations."""
    session = scoped_session(sessionmaker(autocommit=False, autoflush=True, bind=engine))
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        #session.close()
        session.remove()
	pass

# TODO: should consider more carefully how to handle mutex here....
def threaded(fn):
    @wraps(fn)  # functools.wraps
    def wrapper(*args, **kwargs):
	return fn(*args, **kwargs)  
    return wrapper




class ScanFile():
    def __init__(self,repo,relpath,fname):
	self.repo = repo
	self.relpath = relpath
	self.fname = fname
    def __repr__(self):
	return "<ScanFile repo=%d, relpath=%s, fname=%s>" % (self.repo, self.relpath, self.fname)


class UpdateFile():
    def __init__(self,repo,fi):
	self.repo = repo
	self.fi = fi
    def __repr__(self):
	return "<ScanFile repo=%d, fi=%d>" % (self.repo, self.fi)



def validFile(fname, ext):
    if ext.lower() not in validExts:
	logger.debug("file extension not valid: %s #%s#")
	return False
    if re.search(r'^\.',fname):
	logger.debug("ignoring dotfile: %s #%s#")
	return False
    return True
    



#############################################################
#
#  thread classes
#
#############################################################


def FileLoader(repoq,fileq):

    @threaded
    def load(rid):
	def scanError(e):
	    logger.debug("SCAN ERROR !!!!!!!")
	    raise e


	with transaction_context() as session:
	    r = session.query(Repository).get(rid)
	    logger.info("Examining repo: %s" % r)
	    rpath = r.path
	    
	    if not os.path.isdir(rpath):
		logger.error("Repository not found: %s" % rpath)
		return
	    walkargs = {'followlinks':True, 'onerror':'self.scanError'}
	    # recurse
	    for root, dirs, files in os.walk(rpath,**walkargs):
		for f in files:
		    logger.debug("FileLoader walking to %s/%s" % (root, f))
		    fpart,ext = os.path.splitext(f)
		    if not validFile(fpart,ext):
			logger.debug("   not valid filename/extension: %s/%s #%s#" % (root,fpart,ext))
			continue
		    sf = ScanFile(r.id, os.path.relpath(root,rpath), f)
		    logger.debug("adding %s to fileq" % sf)
		    fileq.put(sf)
		

    logger.debug("fileLoader running")
    #while not self.repoq.empty():
    while True:
	rid = repoq.get()
	logger.debug("loading repo %d" % rid)
	load(rid)
	repoq.task_done()

    def scanErro(e):
	raise e



def FileScanner (fileq):

    @threaded
    def considerFile(scanfile):
	with transaction_context() as session:
	    repo = session.query(Repository).filter(Repository.id == str(scanfile.repo)).first()
	    path = scanfile.relpath
	    fname = scanfile.fname

	    
	    fullname = modJoin(repo.path,path,fname)
	    logger.info("considering %s" % fullname)
	    fsize = os.path.getsize(fullname)

	    # shortcut - if this file matches by filename and size, let's avoid md5summing it.
	    q = (session.query(FileInst,File).join(File).filter(File.size == fsize, FileInst.name == fname \
		, FileInst.path == path, FileInst.repository == repo.id).first() )
	    if q:
		(fi,f) = q
		logger.debug(" shortcutting")
		fi.last_seen = datetime.datetime.now()
		fi.deleted_on = None
		session.flush()
		return


	    logger.debug(" checksumming...")
	    fhash = md5sum(fullname)

	    # see if the size matches any recorded file
	    logger.debug("fsize = %d, fhash = %s" % (fsize, fhash))
	    existing = session.query(File).filter(File.size==fsize).filter(File.md5hash==fhash).first()

	    if not existing:
		logger.debug("   no existing file matches - creating file and fileinst")

		f = File(fsize,fhash,fname)
		session.add(f)
		session.flush()
		fi = FileInst(fname, path, repo, f)
		fi.file = f.id
		session.add(fi)
		session.flush()
		return
	    
	    else:
		
		logger.debug("   existing file matches - id = %d " % existing.id)

		# mark as crawled
		existing.last_crawled = datetime.datetime.now()
		session.flush()

		# get corresponding file_insts
		fis = session.query(FileInst,Repository).join(Repository).filter(FileInst.file == existing.id).all()
		logger.debug("   found file and %d existing instances" % int(len(fis)/2) )


		# scan for deleted, mark as seen the rest
		for q in fis:
		    (fi,r) = q
		    logger.debug("updating %s" % modJoin(r.path,fi.path,fi.name))
		    if not os.path.isfile(modJoin(r.path,fi.path,fi.name)):
			fi.deleted_on = datetime.datetime.now()
		    else:
			fi.last_seen = datetime.datetime.now()
		    logger.debug("done update")
		    

		# now that all fileInst have been checked, before creating a new one, let's see if we can fix an old
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
			session.flush()
			return

		    # otherwise, create a new file instance
		    else:
			logger.debug("      creating new instance")
			fi = FileInst(fname,path,repo,existing)
			session.add(fi)
			session.flush()
			return
			    
				
    logger.debug("fileScanner running")
    while True:
	sf = fileq.get()
	considerFile(sf)
	fileq.task_done()



def FileUpdater(updateq):

    @threaded
    def updateFileInst(fi,r):
	with transaction_context() as session:
	    fi = session.query(FileInst).filter(FileInst.id == str(fiid)).first()
	    r = session.query(Repository).filter(Repository.id == str(rid)).first()
	    logger.debug("updating %s" % modJoin(r.path,fi.path,fi.name))
	    if not os.path.isfile(modJoin(r.path,fi.path,fi.name)):
		fi.deleted_on = datetime.datetime.now()
	    else:
		fi.last_seen = datetime.datetime.now()
	    logger.debug("done update")
	    session.flush()


    logger.debug("fileUpdater running")
    while True:
	uf = updateq.get()
	updateFileInst(uf.fi, uf.repo)
	updateq.task_done()


#############################################################
#
#  main
#
#############################################################

# load repositories
rs = session.query(Repository).all()


# walk the files in each repository




logger.debug("adding repos")
for r in rs:
    logger.debug("...enqueuing repository %s" % r)
    rid = r.id
    repoq.put(rid)

# FileLoaders consume repos from the repoq, scan those repos, and add files to the fileq
logger.debug("launching FileLoaders")
for i in range (threadMax if len(rs) > threadMax else len(rs)):
    t = Thread(target=FileLoader, args=(repoq,fileq))
    t.daemon = True  # the prog ends when no alive non-daemons are left
    t.start()

repoq.join() # wait/ensure for everything to be added...
logger.info(" --done enqueuing files (FileLoaders)-- complete %s" % datetime.datetime.now())
logger.debug(" the queue for FileScanners is %d" % fileq.qsize())

# FileScanners consume files from the fileq, analyzes them,  and add records to the database
logger.debug("launching FileScanners")
for i in range (threadMax):
    t  = Thread(target=FileScanner, args=(fileq,)) # requires a tuple
    t.daemon = True  # the prog ends when no alive non-daemons are left
    t.start()

fileq.join()
logger.info(" --done building filelist (FileScanners) -- complete %s" % datetime.datetime.now())



logger.info("###### crawl for new files -- complete %s #######" % datetime.datetime.now())

# check file_instances that we haven't seen in a while
for q in session.query(FileInst,Repository).join(Repository).filter(FileInst.deleted_on == None)\
	.filter(FileInst.last_seen < datetime.datetime.now() - datetime.timedelta(days=3)).yield_per(300):
    (fi,r) = q
    if fi and r:
	uf = UpdateFile(r.id, fi.id)
	updateq.put(uf)

logger.debug("qsize = %d" % updateq.qsize())
if not updateq.empty():
    for i in range (threadMax):
	t = Thread(target=FileUpdater,args=(updateq,))  # requires a tuple
	t.daemon = True  # the prog ends when no alive non-daemons are left
	t.start()

updateq.join()
session.close()
logger.info("###### crawl of files not recently seen -- complete %s #######" % datetime.datetime.now())





