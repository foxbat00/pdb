import os


_basedir = os.path.abspath(os.path.dirname(__file__))

class BaseConfiguration(object):
    SECRET_KEY = 'SecretKeyForSessionSigning'
    DEBUG = True
    Testing = True
    CSRF_ENABLED = True
    CSRF_SESSION_KEY = "something difficult to guess"

    DB_URI = 'postgresql://tgpl@localhost:5432/pdb'

