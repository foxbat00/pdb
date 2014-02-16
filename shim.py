#!/usr/bin/env python
from sqlalchemy import *
import sqlalchemy.dialects as postgres
import sqlalchemy.orm as orm
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import datetime
import re, sys, os
import dateutil.parser as dup

from db import *
import models
from models import *
from util import *


from sqlalchemy.sql import column
s = select([column('display_name')]).select_from[func.active_files()]
q = session.query(s.c.display_name)
print q
print "  --  "
print q.limit(2).all()

