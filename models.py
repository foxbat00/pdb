from sqlalchemy import *
import sqlalchemy.dialects as postgres
import sqlalchemy.orm as orm
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base
import datetime
import re, sys, os

from util import *
from db import *


# REQUIRES sqlalchemy >=0.9.2 to have tsvector support


class Repository(Base):
    __table__ = Table('repository', Base.metadata, autoload=True)
    def __repr__(self): 
	return "<Repository id=%d path=%s>" % (self.id, self.path)




class File(Base):
    __table__ = Table('file', Base.metadata, autoload=True)

    def __init__(self, fsize, fhash, fname):
	self.md5hash = fhash
	self.display_name = fname
	self.size = fsize
	self.last_crawled = datetime.datetime.now()

    def getActiveInst(self):
	return session.query(FileInst).filter(FileInst.deleted_on == None, FileInst.marked_delete != True)\
	    .filter(FileInst.file == self.id).first()
	



class FileInst(Base):
    __table__ = Table('file_inst', Base.metadata, autoload=True)
    Repo = relationship('Repository',backref='FileInsts')
    F = relationship('File',backref='FileInsts')


    def __init__(self, name, path, repo, file):
	self.name = name
	self.path = path
	self.Repo = repo
	self.last_seen = datetime.datetime.now()
	self.marked_delete = False
	self.processed = False
	self.F = file
	#self.file = fileid

    def __repr__(self): 
	return "<FileInst id=%d name=\"%s\", deleted=%s>" % (self.id, modJoin(self.Repo.path,self.path,self.name)\
	    , 'F' if not self.deleted_on else self.deleted_on)

    def getFullName(self):
	return modJoin(self.Repo.path,self.path,self.name)


