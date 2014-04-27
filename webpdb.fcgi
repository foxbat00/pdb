#!/Users/tgpl/envs/py27/bin/python

ALLDIRS = ['/Users/tgpl/envs/py27/lib/python2.7']

import sys 
import site 

# Remember original sys.path.
prev_sys_path = list(sys.path) 

# Add each new site-packages directory.
for directory in ALLDIRS:
  site.addsitedir(directory)

# Reorder sys.path so new directories at the front.
new_sys_path = [] 
for item in list(sys.path): 
    if item not in prev_sys_path: 
        new_sys_path.append(item) 
        sys.path.remove(item) 
sys.path[:0] = new_sys_path 

# make sure my app is in the path too
sys.path.append('/opt/local/www/pdb')

from pdb  import app as application

from flup.server.fcgi import WSGIServer
if __name__ == '__main__':
    WSGIServer(app).run()
