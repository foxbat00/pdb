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
import argparse



# set up db
from db import *
from models import *
from helpers import *

# tagger for tagging new scenes
from tagger import makeFacets, getAliasesAndDict, getTbls

# mover for monitoring space and moving files
import mover


"""
@contextmanager
def transaction_context():
    #Provide a transactional scope around a series of operations.
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
"""



class ScanFile():
    def __init__(self,repo,relpath,fname, fsize):
	self.repo = repo
	self.relpath = relpath
	self.fname = fname
	self.fsize = fsize
    def __repr__(self):
	return "<ScanFile repo=%d, relpath=%s, fname=%s, fsize=%d>" \
	    % (self.repo, self.relpath, self.fname, self.fsize)


class UpdateFile():
    def __init__(self,repo,fi):
	self.repo = repo
	self.fi = fi
    def __repr__(self):
	return "<ScanFile repo=%d, fi=%d>" % (self.repo, self.fi)




#############################################################
#
#  thread classes
#
#############################################################


def FileLoader(repoq,fileq):

    #@threaded
    def load(rid):
	def scanError(e):
	    logger.error("SCAN ERROR !!!!!!!")
	    raise e


	#with transaction_context() as session:
	session = scoped_session(sessionmaker(autocommit=False, autoflush=True, bind=engine))
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
		if re.search(r'^\.',f):
		    continue
		logger.debug("FileLoader walking to %s/%s" % (root, f))
		fsize = os.path.getsize(modJoin(root,f))
		if not validFile(f):
		    continue
		sf = ScanFile(r.id, os.path.relpath(root,rpath), f, fsize)
		#logger.debug("adding %s to fileq" % sf)
		fileq.put(sf)
	    

    logger.info("fileLoader running")
    #while not self.repoq.empty():
    while True:
	rid = repoq.get()
	logger.info("loading repo %d" % rid)
	load(rid)
	repoq.task_done()

    def scanErro(e):
	raise e



def FileScanner (fileq,sceneq):

    #@threaded
    def considerFile(scanfile):


	session = scoped_session(sessionmaker(autocommit=False, autoflush=True, bind=engine)) 
	repo = session.query(Repository).filter(Repository.id == str(scanfile.repo)).first()
	path = scanfile.relpath
	fname = scanfile.fname
	fsize = scanfile.fsize

	
	fullname = modJoin(repo.path,path,fname)
	logger.info("considering %s" % fullname)

	# prevent adding files we can't read for whatever reason
	    # TODO: consider also checking for hash: d41d8cd98f00b204e9800998ecf8427e
	if fsize <= min_file_size:
	    logger.info("====  small file size:   %s size %d " % (fullname, fsize))
	    # when this happens, we need to distinghuish between things like the repo not being
	    # mounted and simply running across a file of size 0...
	    ex = session.query(ForgoneFile) \
		.filter(ForgoneFile.repository_id == repo.id) \
		.filter(ForgoneFile.name == fname) \
		.filter(ForgoneFile.path == path) \
		.first()
	    if ex:
		ex.last_seen = datetime.datetime.now().date()
	    else:
		new = ForgoneFile(fname, path, repo.id)
		session.add(new)
	    session.commit()
	    session.expunge_all()
	    return

	# check for existing
	q = (session.query(FileInst,File).join(File).filter(File.size == fsize, FileInst.name == fname \
	    , FileInst.path == path, FileInst.repository_id == repo.id).first() )
	# shortcut - if this file matches by filename and size, let's avoid md5summing it.
	if q:
	    (fi,f) = q
	    logger.debug(" shortcutting")
	    fi.last_seen = datetime.datetime.now().date()
	    fi.deleted_on = None
	    if not f.display_name:
		f.display_name = fullname
	    if not fi.ext:
		name, ext= os.path.splitext(fname)
		fi.ext = ext
	    sceneq.put(f.id)
	    session.commit()
	    session.expunge_all()
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
	    f.display_name = fname
	    fi = FileInst(fname, path, repo.id, f.id)
	    session.add(fi)
	    session.flush()
	    #createUpdateScene(f)
	    sceneq.put(f.id)
	    session.commit()
	    session.expunge_all()
	    return
	
	else:
	    
	    logger.debug("   existing file matches - id = %d " % existing.id)

	    # mark as crawled
	    existing.last_crawled = datetime.datetime.now().date()
	    session.flush()

	    # if no display name set, set now
	    if not existing.display_name:
		existing.display_name = fullname

	    # if no scene exists, create
	    #createUpdateScene(existing)
	    sceneq.put(existing.id)

	    # get corresponding file_insts
	    fis = session.query(FileInst,Repository).join(Repository).filter(FileInst.file_id == existing.id).all()
	    logger.debug("   found file and %d existing instances" % len(fis))


	    # scan for deleted, mark as seen the rest
	    for q in fis:
		(fi,r) = q
		if r.id not in excludeRepos:
		    logger.debug("updating %s" % modJoin(r.path,fi.path,fi.name))
		    if not os.path.isfile(modJoin(r.path,fi.path,fi.name)):
			# set delete date
			fi.deleted_on = datetime.datetime.now().date()
		    else:
			fi.last_seen = datetime.datetime.now().date()
		    logger.debug("done update")
		

	    # now that all fileInst have been checked, before creating a new one, let's see if we can fix an old
	    # if an instance has been deleted recently, let's reactivate it 
	    # if this file_inst matches a deleted one by words, fully remove the old one (it's a move)
	    for q in fis:
		(fi,r) = q
		d = fi.deleted_on
		if d and d > (datetime.datetime.now().date() - datetime.timedelta(weeks=1) ):
		    if args.enable_file_inst_move and wordmatch(fi.name, mulch(fname)):
			logger.debug("      reactivating old instance")
			fi,r = fis
			fi.name = fname
			fi.path = path
			fi.repository_id = repo.id
			fi.last_seen = datetime.datetime.now().date()
			deleted_on = None
			session.commit()
			session.expunge_all()
			return

	    # otherwise, create a new file instance
	    logger.debug("      creating new instance")
	    fi = FileInst(fname,path,repo.id,existing.id)
	    session.add(fi)
	    session.commit()
	    session.expunge_all()
	    return
		    
			    
    logger.info("fileScanner running")
    while True:
	sf = fileq.get()
	considerFile(sf)
	fileq.task_done()



def FileUpdater(updateq):

    #@threaded
    def updateFileInst(fiid,rid):
	session = scoped_session(sessionmaker(autocommit=False, autoflush=True, bind=engine)) 
	fi = session.query(FileInst).filter(FileInst.id == str(fiid)).first()
	r = session.query(Repository).filter(Repository.id == str(rid)).first()
	logger.debug("updating %s" % modJoin(r.path,fi.path,fi.name))
	if not os.path.isfile(modJoin(r.path,fi.path,fi.name)):
	    fi.deleted_on = datetime.datetime.now().date()
	else:
	    fi.last_seen = datetime.datetime.now().date()
	logger.debug("done update")
	session.commit()
	session.expunge_all()


    logger.info("fileUpdater running")

    while True:
	uf = updateq.get()
	updateFileInst(uf.fi, uf.repo)
	updateq.task_done()






def SceneUpdater(sceneq):

    def createUpdateScene(fid, session):
	if args.no_scenes:
	    return

	file = session.query(File).get(fid)

	# TODO:  consider better check
	scene_id = session.query(SceneFile.scene_id).filter(SceneFile.file_id == file.id).first()
	scene = None

	if not scene_id:
	    scene = Scene(file.display_name)
	    session.add(scene)
	    session.commit()
	    sf = SceneFile(scene.id, file.id)
	    session.add(sf)
	    session.commit()
	    session.expunge(sf)
	else:
	    scene = session.query(Scene).get(scene_id)

	if scene:
	    if not scene.rating:
		m = re.findall(r'^&+|&+$|(?<=\W)&+(?=\W)',file.display_name)
		scene.rating = len(max(m,key=len)) if m else 0
		session.commit()
	    makeFacets(session, scene)  # calls into tagger, expunges and commits
	session.expunge(file)


    logger.info("SceneUpdater running")
    session = scoped_session(sessionmaker(autocommit=False, autoflush=True, bind=engine)) 
    (aliases, apdict) = getAliasesAndDict(session)
    tbls = getTbls(session)

    while True:
	fid = sceneq.get()
	createUpdateScene(fid, session)
	sceneq.task_done()






#############################################################
#
#  main
#
#############################################################


if __name__ == '__main__':

    # globals
    logfile = 'logs/log.txt'
    invalidExts = []
    threadMax = 1
    min_file_size = 80000 # 80k



    # threading queues
    fileq = Queue()
    repoq = Queue()
    sceneq = Queue()
    updateq = Queue()



    # logging
    format = "%(levelname)s (%(threadName)s): %(message)s"
    logging.basicConfig(level=logging.DEBUG, format=format)
    logger = logging.getLogger(__name__)
    logoutput = logging.FileHandler(logfile, mode='w')
    logoutput.setLevel(logging.DEBUG)
    logoutput.setFormatter(logging.Formatter(format))
    logger.addHandler(logoutput)

    logger.setLevel(logging.DEBUG)
    #logger.setLevel(logging.INFO)
    logger.info("==================================================================" )
    logger.info("==================================================================" )
    logger.info(" ")
    logger.info("Crawler initialized  at %s" % datetime.datetime.now() )
    logger.info(" ")
    logger.info("==================================================================" )
    


    # options parsing
    # ARGPARSE argparse
    parser = argparse.ArgumentParser(description='PDB crawler')

    parser.add_argument('-x','--exclude', nargs='+', type=int, help='repositories to exclude from crawl, by id')
    parser.add_argument('--no_scenes',  action='store_true', \
	help='Operate only at the File and FileInst leve - do not create scenes, or apply facets')
    parser.add_argument('--no_mover',  action='store_true', \
	help='turn off functionality for monitoring repo freespace and moving files')
    parser.add_argument('--enable_file_inst_move',  action='store_true', \
	help='When a file_inst has been deleted less than a week ago, reactivate and overwrite rather than' \
	    + 'create a new record')
		
    args = parser.parse_args()

    excludeRepos = []
    if args.exclude:
	for r in args.exclude:
	    logger.info("excluding repository %d" % r)
	    excludeRepos.append(r)

    times = []
    start_time = datetime.datetime.now()


    if not args.no_mover:
	t = ["space check & file move operations", datetime.datetime.now()] 
	logger.info("#### starting %s at %s ####" % (t[0], t[1]))
	source_repo = config.BaseConfiguration.MONITOR_REPO
	dest_repo = config.BaseConfiguration.DEST_REPO
	mover.spaceCheck(source_repo, dest_repo)
	t.append(datetime.datetime.now())
	logger.info("#### completing  %s at %s ####" % (t[0], t[2]))
	times.append(t)


    t = ["new file crawl - loading", datetime.datetime.now()] 
    logger.info("#### starting %s at %s ####" % (t[0], t[1]))



    # load repositories
    rs = session.query(Repository).all()


    # walk the files in each repository




    logger.debug("adding repos")
    for r in rs:
	logger.debug("...enqueuing repository %s" % r)
	rid = r.id
	if rid not in excludeRepos:
	    repoq.put(rid)
	else:
	    logger.debug("excluding repo: %d %s" % (r.id, r.path))




    # FileLoaders consume repos from the repoq, scan those repos, and add files to the fileq
    logger.debug("launching FileLoaders")
    for i in range (threadMax if len(rs) > threadMax else len(rs)):
	thr = Thread(target=FileLoader, args=(repoq,fileq))
	thr.daemon = True  # the prog ends when no alive non-daemons are left
	thr.start()

    repoq.join() # wait/ensure for everything to be added...
    t.append(datetime.datetime.now())
    logger.info("#### completing  %s at %s ####" % (t[0], t[2]))
    times.append(t)





    t = ["new file crawl - scanning", datetime.datetime.now()]
    logger.info("#### starting %s at %s ####" % (t[0], t[1]))

    logger.debug(" the queue for FileScanners is %d" % fileq.qsize())

    # FileScanners consume files from the fileq, analyzes them,  and add records to the database
    logger.debug("launching FileScanners")
    for i in range (threadMax):
	thr  = Thread(target=FileScanner, args=(fileq,sceneq)) # requires a tuple
	thr.daemon = True  # the prog ends when no alive non-daemons are left
	thr.start()

    fileq.join()

    t.append(datetime.datetime.now())
    logger.info("#### completing  %s at %s ####" % (t[0], t[2]))
    times.append(t)








    # update:   check file_instances that we haven't seen since we started the crawl
    t = ["new file crawl - updating", datetime.datetime.now()]
    logger.info("#### starting %s at %s ####" % (t[0], t[1]))
    for q in session.query(FileInst,Repository).join(Repository).filter(FileInst.deleted_on == None)\
	    .filter(FileInst.last_seen < start_time).yield_per(300):
	(fi,r) = q
	if fi and r and r.id not in excludeRepos:
	    uf = UpdateFile(r.id, fi.id)
	    updateq.put(uf)

    session.close()
    logger.debug("update qsize = %d" % updateq.qsize())
    if not updateq.empty():
	for i in range (threadMax):
	    thr = Thread(target=FileUpdater,args=(updateq,))  # requires a tuple
	    thr.daemon = True  # the prog ends when no alive non-daemons are left
	    thr.start()

    updateq.join()

    t.append(datetime.datetime.now())
    logger.info("#### completing  %s at %s ####" % (t[0], t[2]))
    times.append(t)







    # make scenes and tags
    t = ["new file crawl - tagging", datetime.datetime.now()] 
    logger.info("#### starting %s at %s ####" % (t[0], t[1]))
    if not args.no_scenes:
	logger.info(" -- starting scene-level operations- ")
	logger.debug("scene qsize = %d" % updateq.qsize())
	if not sceneq.empty():
	    #for i in range (threadMax):
	    thr = Thread(target=SceneUpdater,args=(sceneq,))  # requires a tuple
	    thr.daemon = True  # the prog ends when no alive non-daemons are left
	    thr.start()

	sceneq.join()

    t.append(datetime.datetime.now())
    logger.info("#### completing  %s at %s ####" % (t[0], t[2]))
    times.append(t)




    logger.info("####################################################")
    total = datetime.timedelta(0)
    for t in times:
	x = t[2]-t[1]
	logger.info( "Phase: %s \t\t\t %s" % (t[0],x) )
	total = total + x
    logger.info("Total time: %s" % total)

