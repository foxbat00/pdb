#!/usr/bin/env python


import argparse
import re
from sqlalchemy import *
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base


from db import *
from util import *

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='pdb search')


    parser.add_argument('-i', action='store_true', default=False, dest='insensitive', help='search case insensitive')
    parser.add_argument('-d', action='store_true', default=False, dest='deleted', help='include deleted files')
    parser.add_argument('terms', nargs='+', type=str, help='search terms (AND implicit)')
    args = parser.parse_args()

    q = session.query(FileInst)
    if not args.deleted:
	q = q.filter(FileInst.deleted_on == None)
    for term in args.terms:
	    if args.insensitive:
		q = q.filter( (FileInst.path.ilike("%%%s%%" % term)) | (FileInst.name.ilike("%%%s%%" % term)) )
	    else:
		q = q.filter( (FileInst.path.like("%%%s%%" % term)) | (FileInst.name.like("%%%s%%" % term)) )
	
    for x in q.all():
	print x.getFullName()
