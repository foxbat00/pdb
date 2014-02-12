from flask import Blueprint, Response, render_template, flash, redirect, session, url_for, request, abort
from models import *
from db import session, Base
from datetime import datetime
from sqlalchemy import *
import mimetypes
import os



mod = Blueprint('contents', __name__)



@mod.route('/content/<repoid>/<fileid>', methods=('GET'))
#@login_required
def get_content(repoid, fileid):
    r = Repository.get(repoid)
    f = File.get(fileid)
    if not r and f:   # and has higher precedence than not
	return abort(404)
    if not f.deleted_on and f.marked_delete!=True:
	return abort(404)
    fi = f.getActiveInst()
    fqname = fi.getFullName()
    filename = fi.name
    mimetype = mimetypes.guess_type(filename)[0]
    if not os.path.isfile(fqname):
	return abort(404)
    else:
	return Response(generate(fqname), mimetype=mimetype)


def generate(fqname):
    chunk = 1024*16
    with open(fqname,'rb') as f:
	for chunk in iter(lambda: f.read(chunk),b''):
	    yield chunk

	    
	    
