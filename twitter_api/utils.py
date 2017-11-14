from functools import wraps
import hashlib
import sqlite3

from flask import request, g, abort
JSON_MIME_TYPE = 'application/json'


def retrieve_resource(resource_type, *args, **kwargs):
    curs = g.db.cursor()
    if not args:
        select_list = "*"
    else:
        select_list = ", ".join(args)
    query = "SELECT {columns} from {table}".format(table=resource_type, columns=select_list)
    if kwargs:
        parameterized_where_clause = " AND ".join([k + "=" + ":" + k for k in kwargs.keys()])
        query+= " where " + parameterized_where_clause
    curs.execute(query, kwargs)
    resource = curs.fetchall()
    return resource


def md5(token):
     """
     Returns an md5 hash of a token passed as a string, performing an internal 
     conversion of the token to bytes if run in Python 3
     """
     m = hashlib.md5()
     m.update(token)
     return m

def get_user_from_token(req, token_attr):
    user_id_list = retrieve_resource("auth","user_id",access_token=req[token_attr])
    if user_id_list:
        return user_id_list[0]
    return None
    
def auth_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        req = request.get_json()
        if 'access_token' in req:
            print ("**auth_only req" + str(req))
            user_id = get_user_from_token(req, 'access_token')
            if user_id:
                return f(*args, **kwargs)
        abort(401)
    return decorated_function


def json_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.content_type != 'application/json':
            abort(400)
        return f(*args, **kwargs)
    return decorated_function
