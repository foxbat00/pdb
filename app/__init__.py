from flask import Flask, request, render_template, send_from_directory
from db import Base, session
import os
from config import *


app = Flask(__name__) #create our application object


# disable until needed

#from app.content.views import mod as contentModule
#app.register_blueprint(contentModule)


app.config.from_object('config.BaseConfiguration')


from models import *
from app.views import *
from app.forms import *


#hack to get reload on template changes when templates not passed through render_template:
def extra_files(extradirs):
    extra_files = extradirs[:]
    for extra_files in extra_dirs:
	for dirname, dirs, files, in os.walk(extra_dir):
	    for filename in files:
		filename = path.join(dirname,filename)
		if path.isfile(filename):
		    extra_files.append(filename)
    return extra_files


#----------------------------------------
# controllers
#----------------------------------------


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'ico/favicon.ico')


@app.route("/")
def index():
    stats = {}
    stats['total_file_inst'] =  "{:,}".format(int(session.query(FileInst).count() ))
    stats['total_file'] =	"{:,}".format(int(session.query(File).count() ))
    stats['total_scene'] =	"{:,}".format(int(session.query(Scene).count() ))
    stats['total_star'] =	"{:,}".format(int(session.query(Star).count()  ))
    stats['total_series'] =	"{:,}".format(int(session.query(Series).count()  ))
    stats['total_data'] =	int( \
	session.query(func.sum(File.size)) \
	.join(FileInst, File.id == FileInst.file_id) \
	.filter(FileInst.deleted_on == None, FileInst.marked_delete != True) \
	.scalar()   )
    return render_template('index.html', stats=stats)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(400)
def key_error(e):
    app.logger.warning('Invalid request resulted in KeyError', exc_info=e)
    return render_template('400.html'), 400


@app.errorhandler(500)
def internal_server_error(e):
    app.logger.warning('An unhandled exception is being displayed to the end user', exc_info=e)
    return render_template('generic.html'), 500


@app.errorhandler(Exception)
def unhandled_exception(e):
    app.logger.error('An unhandled exception is being displayed to the end user', exc_info=e)
    return render_template('generic.html'), 500


@app.before_request
def log_entry():
    app.logger.debug("Handling request")


@app.teardown_request
def log_exit(exc):
    app.logger.debug("Finished handling request", exc_info=exc)

@app.teardown_appcontext
def shutdown_session(exception=None):
    session.remove()

#----------------------------------------
# logging
#----------------------------------------

import logging


class ContextualFilter(logging.Filter):
    def filter(self, log_record):
        log_record.url = request.path
        log_record.method = request.method
        log_record.ip = request.environ.get("REMOTE_ADDR")
        #log_record.user_id = -1 if current_user.is_anonymous() else current_user.get_id()

        return True

context_provider = ContextualFilter()
app.logger.addFilter(context_provider)
del app.logger.handlers[:]

handler = logging.StreamHandler()

log_format = "%(asctime)s\t%(levelname)s\t%(ip)s\t%(method)s\t%(url)s\t%(message)s"
formatter = logging.Formatter(log_format)
handler.setFormatter(formatter)

app.logger.addHandler(handler)

from logging import ERROR
from logging.handlers import TimedRotatingFileHandler

# Only set up a file handler if we know where to put the logs
if app.config.get("ERROR_LOG_PATH"):

    # Create one file for each day. Delete logs over 7 days old.
    file_handler = TimedRotatingFileHandler(app.config["ERROR_LOG_PATH"], when="D", backupCount=7)

    # Use a multi-line format for this logger, for easier scanning
    file_formatter = logging.Formatter('''
    Time: %(asctime)s
    Level: %(levelname)s
    Method: %(method)s
    Path: %(url)s
    IP: %(ip)s

    Message: %(message)s

    ---------------------''')

    # Filter out all log messages that are lower than Error.
    file_handler.setLevel(ERROR)

    file_handler.addFormatter(file_formatter)
    app.logger.addHandler(file_handler)
