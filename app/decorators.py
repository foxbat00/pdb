from flask import Blueprint, Response, render_template, flash, redirect, session, url_for, request, jsonify, abort
from app import app
from db import session, Base
from models import *
from datetime import datetime
from sqlalchemy import *
from app.browse.forms import BrowseForm
import json
from functools import wraps





#### Decorator for view functions to check for PJAX header
  ## returns 403 error if PJAX header not detected

def xpjax_only(view_function):
    @wraps(view_function)
    # the new, post-decoration function. Note *args and **kwargs here.
    def decorated_function(*args, **kwargs):
	if "X-PJAX" in request.headers:
            return view_function(*args, **kwargs)
        else:
	    app.logger.error('ERROR:  non-PJAX request to PJAX route')
            abort(403)
    return decorated_function


