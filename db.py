#!/usr/bin/env python
from sqlalchemy import *
import sqlalchemy.dialects as postgres
import sqlalchemy.orm as orm
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base
import datetime
import re, sys, os

from util import *



engine = create_engine('postgresql://tgpl@localhost:5432/pdb')
engine.echo = False
session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()
Base.metadata.bind = engine


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



class FileInst(Base):
    __table__ = Table('file_inst', Base.metadata, autoload=True)
    Repo = relationship('Repository',backref='FileInsts')
    F = relationship('File',backref='FileInsts')


    def __init__(self, name, path, repo,filerec):
	self.name = name
	self.path = path
	self.Repo = repo
	self.last_seen = datetime.datetime.now()
	self.marked_delete = False
	self.processed = False
	self.F = filerec

    def __repr__(self): 
	return "<FileInst id=%d name=\"%s\", deleted=%s>" % (self.id, modJoin(self.Repo.path,self.path,self.name)\
	    , 'F' if not self.deleted_on else self.deleted_on)
    def getFullName(self):
	return modJoin(self.Repo.path,self.path,self.name)


