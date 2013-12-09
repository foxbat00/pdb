#!/usr/bin/env python

import hashlib
import os
import re

# avoid '.' winding up in assembled paths
def modJoin(*paths):
    return os.path.join(*[x for x in paths if x != '.'])



def md5sum(file):
    md5 = hashlib.md5()
    with open(file,'rb') as f:
	for chunk in iter(lambda: f.read(128*md5.block_size),b''):
	    md5.update(chunk)
    return md5.hexdigest()

