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



# set up db
from db import *
from models import *
import models # needed for getattr magic
from util import *
session = scoped_session(sessionmaker(autocommit=False, autoflush=True, bind=engine))

# logging
format = "%(levelname)s (%(threadName)s): %(message)s"
logging.basicConfig(level=logging.DEBUG, format=format)
logger = logging.getLogger(__name__)
logoutput = logging.FileHandler(logfile, mode='w')
logoutput.setLevel(logging.DEBUG)
logoutput.setFormatter(logging.Formatter(format))
logger.addHandler(logoutput)

#logger.setLevel(logging.INFO)





# collect files that have no scene
for file in session.query(File).filter(not_(exists().where(SceneFile.file_id == File.id))).yield_per(200):


    logger.debug("..%s" % display_name)
    # make tentative scene
    scene = Scene(file.name)
    session.add(scene)
    session.flush()
    sf = SceneFile(scene.id, file.id)
    session.add(sf)
    session.commit()
    

