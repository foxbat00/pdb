#!/usr/bin/env python
from app import app
import os, re


# TODO:  figure out how to move this into config.py (and possibly also define port # there)
DIRS_TO_MONITOR_FOR_RELOAD = ['app/templates','app/static']
#hack to get reload on template changes when templates not passed through render_template:
def extra_files(extra_dirs):
    extra_files = extra_dirs[:]
    for extra_dir in extra_dirs:
        for dirname, dirs, files, in os.walk(extra_dir):
            for filename in files:
		filename = os.path.join(dirname,filename)
		if os.path.isfile(filename) and not re.search(r'\.swp$',filename):
		    extra_files.append(filename)
    return extra_files

if __name__ == '__main__':
    app.run(debug=True, extra_files = extra_files(DIRS_TO_MONITOR_FOR_RELOAD))
