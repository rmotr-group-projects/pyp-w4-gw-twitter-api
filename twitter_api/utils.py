import hashlib
import string
import random
from functools import wraps
import datetime
from flask import make_response, request, abort, g

JSON_MIME_TYPE = 'application/json'


def generate_random_token(size=15):
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(size))


def md5(token):
    """
    Returns an md5 hash of a token passed as a string, performing an internal
    conversion of the token to bytes if run in Python 3

    Intuition: You don't want the plaintext version of the password to be stored in the database. If someone where to gain access to the database, they would get your password and your account would now be comprimised. To avoid this, the passwords are first hashed (jumbled up) before being stored in the database. Thus, only the user himself knows the real, plaintext, password. In the database, only the hashed version of the password is stored. By construction, it is very difficult to derive the original plaintext password from its hash.
    """
    new_token = token
    if str != bytes:
        new_token = token.encode('utf-8')
    return hashlib.md5(new_token)


def sqlite_date_to_python(date_str):
    if date_str is None:
        return None
    return datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")


def python_date_to_json_str(dt):
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def auth_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        if 'access_token' not in request.json:
            abort(401)

        # get user_id that matches access token from auth database
        query = """
            SELECT user_id FROM auth
            WHERE access_token=:access_token;
        """
        param = {'access_token': request.json['access_token']}
        cursor = g.db.execute(query, param)
        user_id = cursor.fetchone()

        # check access token provided in **kwargs through the post request
        # abort with unauthorized request status code if user with given
        # access token does not exist
        if not user_id:
            abort(401)

        # return as user id
        kwargs['user_id'] = user_id[0]

        return f(*args, **kwargs)
    return decorated_function


def json_only(f):
    """Check if data provided is in json format"""
    @wraps(f)
    def decorated_function(*args, **kwargs):

        if request.content_type != JSON_MIME_TYPE:
            abort(400)

        return f(*args, **kwargs)

    return decorated_function


def json_response(data='', status=200, headers=None):
    headers = headers or {}
    if 'Content-Type' not in headers:
        headers['Content-Type'] = JSON_MIME_TYPE

    return make_response(data, status, headers)
