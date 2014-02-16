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



from sqlalchemy.sql import column
# snippet to use in querying against only active files for jquery
def active_files(*fields):
    from_clause = select_from(func.active_files()).alias('active_files')
    if not fields:
        return select([column('display_name')]).from_clause
    else:
        field_list = []
        for f in fields:
            field_list.append(column(f))
        return selec(field_list).from_clause



###### auto reflection tables and some inits #####  


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


class Scene(Base):
    __table__ = Table('scene', Base.metadata, autoload=True)

    def __init__(self, name):
	self.display_name = name 

    def __repr__(self): 
	return "<Scene id=%d name=\"%s\">" % (self.id, self.name)




class Tag(Base):
    __table__ = Table('tag', Base.metadata, autoload=True)
    def __repr__(self): 
	return "<Tag id=%d name=\"%s\">" % (self.id, self.name)

class Star(Base):
    __table__ = Table('star', Base.metadata, autoload=True)
    def __repr__(self): 
	return "<Star id=%d name=\"%s\">" % (self.id, self.name)

class Label(Base):
    __table__ = Table('label', Base.metadata, autoload=True)
    def __repr__(self): 
	return "<Label id=%d name=\"%s\">" % (self.id, self.name)

class Alias(Base):
    __table__ = Table('alias', Base.metadata, autoload=True)
    def __repr__(self): 
	return "<Alias id=%d name=\"%s\">" % (self.id, self.name)

class Series(Base):
    __table__ = Table('series', Base.metadata, autoload=True)
    def __repr__(self): 
	return "<Series id=%d name=\"%s\">" % (self.id, self.name)



# mapping tables

class SceneFile(Base):
    __table__ = Table('scene_file', Base.metadata, autoload=True)

    def __init__(self, scene_id, file_id):
	self.scene_id = scene_id 
	self.file_id = file_id 

class SceneTag(Base):
    __table__ = Table('scene_tag', Base.metadata, autoload=True)

    def __init__(self, scene_id, tag_id):
	self.scene_id = scene_id 
	self.tag_id = tag_id 

class SceneStar(Base):
    __table__ = Table('scene_star', Base.metadata, autoload=True)

class AliasStar(Base):
    __table__ = Table('alias_star', Base.metadata, autoload=True)

class AliasLabel(Base):
    __table__ = Table('alias_label', Base.metadata, autoload=True)

class AliasSeries(Base):
    __table__ = Table('alias_series', Base.metadata, autoload=True)


 
# tagging

class AliasRules(Base):
    __table__ = Table('alias_rules', Base.metadata, autoload=True)

class AliasImplic(Base):
    __table__ = Table('tag_implications', Base.metadata, autoload=True)




