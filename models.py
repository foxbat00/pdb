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
	    , 'F' if not self.deleted_on and not self.marked_delete else self.deleted_on)

    def getFullName(self):
	return modJoin(self.Repo.path,self.path,self.name)


class Scene(Base):
    __table__ = Table('scene', Base.metadata, autoload=True)

    def __init__(self, name):
	self.display_name = name 

    def __repr__(self): 
	return "<Scene id=%d display_name=\"%s\">" % (self.id, self.display_name)

    def isDeleted(self):
	return not session.query(FileInst) \
	    .join(File, FileInst.file == File.id) \
	    .join(SceneFile, SceneFile.file_id == File.id) \
	    .filter(FileInst.deleted_on == None, FileInst.marked_delete == False) \
	    .filter(SceneFile.scene_id == self.id) \
	    .first()




class Tag(Base):
    __table__ = Table('tag', Base.metadata, autoload=True)
    def __repr__(self): 
	return "<Tag id=%d name=\"%s\">" % (self.id, self.name)
    def __init__(self, name):
	self.name = name 

class Star(Base):
    __table__ = Table('star', Base.metadata, autoload=True)
    def __repr__(self): 
	return "<Star id=%d name=\"%s\">" % (self.id, self.name)
    def __init__(self, name):
	self.name = name 
	self.gender='f'

class Label(Base):
    __table__ = Table('label', Base.metadata, autoload=True)
    def __repr__(self): 
	return "<Label id=%d name=\"%s\">" % (self.id, self.name)
    def __init__(self, name):
	self.name = name 

class Alias(Base):
    __table__ = Table('alias', Base.metadata, autoload=True)
    def __repr__(self): 
	return "<Alias id=%d name=\"%s\">" % (self.id, self.name)
    def __init__(self, name):
	self.name = name 

class Series(Base):
    __table__ = Table('series', Base.metadata, autoload=True)
    def __repr__(self): 
	return "<Series id=%d name=\"%s\">" % (self.id, self.name)
    def __init__(self, name):
	self.name = name 



# mapping tables

class SceneFile(Base):
    __table__ = Table('scene_file', Base.metadata, autoload=True)

    def __init__(self, scene_id, file_id, tentative=True):
	self.scene_id = scene_id 
	self.file_id = file_id 
	self.tentative = tentative
    def __repr__(self): 
	return "<SceneFile scene_id=%d file_id=%d tentative=%s>" % (self.scene_id, self.file_id, self.tentative)

class SceneTag(Base):
    __table__ = Table('scene_tag', Base.metadata, autoload=True)

    def __init__(self, scene_id, tag_id, tentative=True):
	self.scene_id = scene_id 
	self.tag_id = tag_id 
	self.tentative = tentative
    def __repr__(self): 
	return "<SceneTag scene_id=%d tag_id=%d tentative=%s>" % (self.scene_id, self.tag_id, self.tentative)

class SceneStar(Base):
    __table__ = Table('scene_star', Base.metadata, autoload=True)

    def __init__(self, scene_id, star_id, tentative=True):
	self.scene_id = scene_id 
	self.star_id = star_id 
	self.tentative = tentative
    def __repr__(self): 
	return "<SceneStar scene_id=%d star_id=%d tentative=%s>" % (self.scene_id, self.star_id, self.tentative)




class AliasTag(Base):
    __table__ = Table('alias_tag', Base.metadata, autoload=True)

    def __init__(self, alias_id, tag_id, tentative=True):
	self.alias_id = alias_id
	self.tag_id = tag_id
	self.tentative = tentative

    def __repr__(self): 
	return "<AliasTag alias_id=%d tag_id=%d tentative=%s" % (self.alias_id, self.tag_id, self.tentive)


class AliasStar(Base):
    __table__ = Table('alias_star', Base.metadata, autoload=True)

    def __init__(self, alias_id, star_id, tentative=True):
	self.alias_id = alias_id
	self.star_id = star_id
	self.tentative = tentative

    def __repr__(self): 
	return "<AliasStar alias_id=%d star_id=%d tentative=%s" % (self.alias_id, self.star_id, self.tentive)

class AliasLabel(Base):
    __table__ = Table('alias_label', Base.metadata, autoload=True)

    def __init__(self, alias_id, label_id, tentative=True):
	self.alias_id = alias_id
	self.label_id = label_id
	self.tentative = tentative

    def __repr__(self): 
	return "<AliasLabel alias_id=%d label_id=%d tentative=%s" % (self.alias_id, self.label_id, self.tentive)

class AliasSeries(Base):
    __table__ = Table('alias_series', Base.metadata, autoload=True)

    def __init__(self, alias_id, series_id, tentative=True):
	self.alias_id = alias_id
	self.series_id = series_id
	self.tentative = tentative


    def __repr__(self): 
	return "<AliasSeries alias_id=%d series_id=%d tentative=%s" % (self.alias_id, self.series_id, self.tentive)

 
# tagging


class FacetImplic(Base):
    __table__ = Table('facet_implication', Base.metadata, autoload=True)

    def __init__(self, predicate, predicate_type, target, target_type, operator="+"):
	self.predicate = predicate
	self.predicate_type = predicate_type
	self.target = target
	self.target_type = target_type
	self.operator = operator


    def __repr__(self): 
	return "<FacetImplic %s:%d => %s:%d" \
	    % (self.predicate_type, self.predicate, self.target_type, self.target)


