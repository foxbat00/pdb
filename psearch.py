#!/usr/bin/env python


import argparse
import re
from sqlalchemy import *
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base


from db import *
from util import *
from models import *

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='pdb search')


    parser.add_argument('-i', action='store_true', default=True, dest='insensitive', help='search case insensitive')
    parser.add_argument('-d', action='store_true', default=False, dest='deleted', help='include deleted files')
    parser.add_argument('terms', nargs='+', type=str, help='search terms')
    args = parser.parse_args()

    q = session.query(Scene)
    if not args.deleted:
	q = q.filter(FileInst.deleted_on == None)
    for term in args.terms:
	    if args.insensitive:
		q = q.filter( Scene.wordbag.ilike("%%%s%%" % term) )
	    else:
		q = q.filter( Scene.wordbag.like("%%%s%%" % term) )
	
    for scene in q.all():
	print " "
	print " "
	print 'Scene:  id=%d, dn=%s' % (scene.id, scene.display_name)
	fis = scene.get_file_insts()
	for fi in fis:
	    print " -- %s" % fi
