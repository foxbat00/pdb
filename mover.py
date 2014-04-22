#!/usr/bin/env python
from sqlalchemy import *
import sqlalchemy.dialects as postgres
from sqlalchemy.orm import scoped_session, sessionmaker
import datetime
import re, sys, os
import logging 
import time

from  hurry.filesize import size as hurrysize
import shutil



# set up db
from db import *
from models import *
from helpers import *


max_files = 1000
folder_name = 'unsorted'
naming_convention = r'(%s)(\d+)' % folder_name
b2g = 1024 ** 3
space_threshold = 10   # move files when less than this amount of freespace is left
space_threshold = space_threshold * b2g
move_threshold = 15  # move at least this amount of data in each move
move_threshold = move_threshold * b2g

bDebug = False


logfile = 'logs/mover-log.txt'
format = "%(levelname)s (%(threadName)s): %(message)s"
logging.basicConfig(level=logging.DEBUG, format=format)
logger = logging.getLogger(__name__)
logoutput = logging.FileHandler(logfile, mode='w')
logoutput.setLevel(logging.DEBUG)
logoutput.setFormatter(logging.Formatter(format))
logger.addHandler(logoutput)


# get list of files ordered by modtime asc (oldest first)
def get_recent_files(sourcer):
    filelist = []
    for name in os.listdir(sourcer.path):
	fullpath = os.path.join(sourcer.path,name)
	a = os.stat(fullpath)
	#          0      1            2         3
	# entry = [path, mod time, create time, size]  len = 4
	entry = [fullpath,a.st_mtime,a.st_ctime] #[file,last_modified,created]

	if os.path.isfile(fullpath):
	    entry.append(os.path.getsize(fullpath))
	elif os.path.isdir(fullpath):
	    (size, mt) = get_recursive_file_data(fullpath)
	    entry.append(size)
	    if mt < entry[1]:
		entry[1] = mt
	else:
	    continue
	if len(entry) != 4:
	    logger.debug('!!!!!!!! about to add deficient entry: %s' % entry)
	filelist.append(entry)

    # sort on mod date
    newlist = sorted(filelist, key = lambda tup: tup[1])
    return newlist






def spaceCheck(source_repo, dest_repo):


    #  determine free space situation
    sourcer = session.query(Repository).get(source_repo)
    s = os.statvfs(sourcer.path)
    freespace = (s.f_bavail * s.f_frsize) 

    logger.debug('free space available on %s: %s' % (sourcer.path, hurrysize(freespace))   )
    logger.debug('threshold for moving is  set at  %s' % hurrysize(space_threshold) )
    
    if freespace < space_threshold:
	logger.debug('move undertaken, move threshold is set at  %s' % (hurrysize(move_threshold))  )
	
	# prepare to move
	destr = session.query(Repository).get(dest_repo)


	# figure out which unsorted directory is current, and if it needs changing
	def getDestPath(repo):


	    last = 0
	    base = ''
	    file_count = 0
	    destdir = ''
	    for name in os.listdir(repo.path):
		fullpath = os.path.join(repo.path,name)
		if os.path.isdir(fullpath):
		    num = re.findall(naming_convention, name)
		    if num and int(num[0][1]) > last:
			last = int(num[0][1])
			base = num[0][0]
			destdir = fullpath
		if not re.findall(r'^\.\.?', name):
		    file_count = file_count + 1

	    if file_count > max_files:
		destdir = repo.path + '/' + base + str(last + 1)
	    return destdir


	dest_path = getDestPath(destr)
	logger.debug("destination directory: %s" % dest_path)




	
	filelist = get_recent_files(sourcer)
	total = 0
	movelist = []
	for n in filelist:
	    #logger.debug("newlist loop: %s, size = %d" % (n[0], n[3]) )
	    #logger.debug('total = %d' % total)
	    total +=  n[3]
	    movelist.append((n[0], n[3]))
	    if total > move_threshold:
		break
	
	# move
	for n in movelist:

	    (f,s) = n

	    logger.debug( "moving  %s to %s" % (f, dest_path))

	    # figure out if file exists in db already
	    q = session.query(FileInst)
	    relpath = os.path.relpath(f,sourcer.path)

	    # accepts source repo, dest repo, destination path relative to repo, filename, filesize
	    def adjustFileInst(sourcer,destr,p,f,s):
		#logger.debug("sourcer = %s; destr = %s; p = %s; f = %s; s = %s"  \
		    #% (sourcer.path, destr.path, p, f, s) )
		fpart,ext = os.path.splitext(f)
		if ext.lower() in validExts:
		    existing  = q.join(File) \
			.filter(FileInst.repository_id == sourcer.id) \
			.filter(FileInst.name == f) \
			.filter(FileInst.path == p) \
			.filter(File.size == s) \
			.first()
		    if existing:
			logger.debug("  existing found: %s" % existing)
			existing.repository_id = destr.id
			existing.path = os.path.relpath(dest_path,destr.path)
			existing.last_seen = datetime.datetime.now()
			if not bDebug:
			    logger.debug("  existing fixed: %s" % existing)
			else:
			    logger.debug("  existing NOT fixed (debug mode): %s" % existing)


	    if os.path.isfile(f):
		filename = os.path.split(relpath)[-1]
		#p = os.path.split(relpath)[:-1][0]
		#logger.debug('FILE: f = %s; filename = %s; d = %s, s = %s' % (f,filename, d, s) )
		adjustFileInst(sourcer,destr,dest_path, filename, s)
	    else: # directory - recursively check files within
		relpath = os.path.relpath(f,sourcer.path)
		for root, dirs, files in os.walk(f):
		    for file in files:
			s = os.path.getsize(os.path.join(root,file))
			adjustFileInst(sourcer,destr, os.path.relpath(root, sourcer.path), file, s)


	    # otherwise, it's not been crawled yet; let's move it and let the crawler find it at the destination
	    if not bDebug:
		try:
		    if os.path.exists(os.path.join(dest_path,os.path.relpath(f,sourcer.path))):
			logger.error("ERROR: tried to move %s but file with same name already existing at %s" \
			    % (f,dest_path) )
			session.rollback()
		    else:
			shutil.move(f,dest_path)
			session.commit()
		except shutil.Error:
		    session.rollback()
		    logger.error("ERROR: file not moved, due to shutil error")
	    else:
		session.rollback()
		
	    



	





