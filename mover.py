#!/usr/bin/env python
from sqlalchemy import *
import sqlalchemy.dialects as postgres
from sqlalchemy.orm import scoped_session, sessionmaker
import datetime
import dateutil.parser as dup
import re, sys, os
from Queue import Queue
import logging 
import time



# set up db
from db import *
from models import *
from helpers import *


max_files = 1000
naming_convention = r'(unsorted)(\d+)'
space_threshold = 10 
space_threshold = space_threshold * 1024 * 1024 * 1024 # convert from gigs 
move_threshold = 15
move_threshold = move_threshold * 1024 * 1024 * 1024 # convert from gigs 

bDebug = True





def spaceCheck(source_repo, dest_repo)

    #  determine free space situation
    sourcer = session.query(Repo).get(source_repo)
    s = os.statvfs(sourcer.path)
    freespace = (s.f_bavail * s.f_frsize) / 1024
    
    if freespace < space_threshold:
	
	# prepare to move
	fileq = Queue()
	destr = session.query(Repo).get(dest_repo)


	# figure out which unsorted directory is current, and if it needs changing
	def getDestPath(repo):


	    last = 0
	    base = ''
	    file_count = 0
	    destdir = ''
	    for name in os.listdir(repo.path):
		fullpath = os.path.join(repo.path,name)
		if os.path.isdir(fullpath):
		    num = re.findall(naming_convention, subdir)
		    if num and num > last:
			last = num[0][1]
			base = num[0][0]
			destdir = fullpath
		if not re.findall(r'^\.\.?', name):
		    file_count = file_count + 1

	    if file_count > max_files:
		destdir = repo.path + '/' + base + str(last + 1)
	    return last


	dest_path = getDestPath(destr)


	# get most reecent files
	filelist = []
	for name in os.listdir(destr.path):
	    fullpath = os.path.join(destr.path,name)
	    a = os.stat(fullpath)
	    entry = [fullpath,time.ctime(a.st_mtime),time.ctime(a.st_ctime)] #[file,last_modified,created]

	    if os.path.isfile(fullpath):
		entry.append(os.path.getsize(fullpath)
	    elif os.path.isdir(fullpath):
		size = get_recursize_size(fullpath)
		entry.append(size)
	    else:
		continue
	    filelist.append(entry)
	
	total = 0
	newlist = sorted(filelist, reverse = True, key = lambda pair: pair[2])
	for n in newlist:
	    total = total + n[3]
	    movelist.append(n[0], n[3])
	    if total > move_threshold:
		break
	
	# move
	for n in newlist:

	    f = n[0]
	    s = n[1]

	    logger.debug( "move %s to %s" % (f, dest_path))

	    # figure out if file exists in db already
	    if not bDebug:
		q = session.query(FileInst)
		relpath = os.path.relpath(f,sourcer.path)

		def adjustFileInst(sourcer,destr,p,f,s):
		    fpart,ext = os.path.splitext(f)
		    if ext.lower() in validExts::
		    existing  = q.filter(f.repository_id == sourcer.id).filter(FileInst.name == f) \
			.filter(FileInst.path == d).filter(FileInst.size == s).first()
		    if existing:
			logger.debug("Mover: existing found: %s" % existing)
			existing.repository_id = destr.id
			existing.path = os.path.relpath(destdir,destr.path)
			existing.last_seen = datetime.datetime.now()
			session.commit()
			logger.debug("Mover: existing fixed: %s" % existing)


		if os.path.isfile(f)
		    filename = os.path.split(relpath)[-1]
		    d = os.path.split(relpath)[:-1][0]
		    adjustFileInst(sourcer,destr,d, filename, s):
		else: # directory - recursively check files within
		    relpath = os.path.relpath(f,sourcer.path)
		    for root, dirs, files in os.walk(f,**walkargs):
			for f in files:
			    s = os.path.getsize(f)
			    adjustFileInst(sourer,destr, os.path.relpath(root, sourcer.path), f, s)


	    # otherwise, it's not been crawled yet; let's move it and let the crawler find it at the destination
	    if not bDebug:
		shutil.move(f,dest_path)
		
	    



	





