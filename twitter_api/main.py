import json
import psycopg2

from flask import Flask
from flask import g, request, url_for, abort

from .utils import (
    json_only, auth_only, md5, generate_random_token,
    python_date_to_json_str, sqlite_date_to_python)


JSON_MIME_TYPE = 'application/json'

app = Flask(__name__)


def connect_db():
    return psycopg2.connect(app.config['DATABASE_URL'])


@app.before_request
def before_request():
    g.db = connect_db()


@app.route('/login', methods=['POST'])
@json_only
def login():
    if not all([request.json.get(k, None) for k in ['username', 'password']]):
        abort(400)
    username = request.json['username']
    password = request.json['password']

    query = "SELECT id, username, password from twitter_user WHERE username=%(username)s;"
    cursor = g.db.cursor()
    cursor.execute(query, {'username': username})
    user = cursor.fetchone()
    if user is None:
        abort(404)

    user_id, usr, pw = user
    if md5(password).hexdigest() != pw:
        abort(401)

    # All good!
    access_token = generate_random_token()
    query = """INSERT INTO auth ("user_id", "access_token")
               VALUES (%(user_id)s, %(access_token)s);"""
    params = {'user_id': user_id, 'access_token': access_token}

    try:
        cursor = g.db.cursor()
        cursor.execute(query, params)
        g.db.commit()
    except sqlite3.IntegrityError:
        abort(500)
    else:
        return json.dumps({
            'access_token': access_token
        }), 201, {'Content-Type': JSON_MIME_TYPE}


@app.route('/logout', methods=['POST'])
@auth_only
def logout(user_id):
    query = """
        DELETE FROM auth WHERE user_id = %(user_id)s;
    """
    params = {'user_id': user_id}
    cursor = g.db.cursor()
    cursor.execute(query, params)
    g.db.commit()
    return "", 204


@app.route('/tweet/<int:tweet_id>')
def get_tweet(tweet_id):
    query = """SELECT t.id, t.content, t.created, u.username
        FROM tweet t INNER JOIN twitter_user u ON u.id == t.id
        WHERE t.id=%(tweet_id)s;
    """
    cursor = g.db.cursor()
    cursor.execute(query, {'tweet_id': tweet_id})
    tweet = cursor.fetchone()
    if tweet is None:
        abort(404)

    t_id, content, dt, username = tweet
    data = {
        "id": t_id,
        "content": content,
        "date": python_date_to_json_str(sqlite_date_to_python(dt)),
        "profile": "/profile/%s" % username,
        "uri": "/tweet/%s" % t_id
    }
    return json.dumps(data), 200, {'Content-Type': JSON_MIME_TYPE}


@app.route('/tweet', methods=["POST"])
@json_only
@auth_only
def post_tweet(user_id):
    if 'content' not in request.json:
        abort(400)

    query = """INSERT INTO tweet ("user_id", "content")
               VALUES (%(user_id)s, %(content)s);"""
    params = {'user_id': user_id, 'content': request.json['content']}
    try:
        cursor = g.db.cursor()
        cursor.execute(query, params)
        g.db.commit()
    except sqlite3.IntegrityError:
        abort(500)
    else:
        return "", 201


@app.route('/tweet/<int:tweet_id>', methods=["DELETE"])
@json_only
@auth_only
def delete_tweet(tweet_id, user_id):
    query = "SELECT t.id, t.user_id FROM tweet t WHERE t.id=%(tweet_id)s;"
    params = {'user_id': user_id, 'tweet_id': tweet_id}
    cursor = g.db.cursor()
    cursor.execute(query, params)
    tweet = cursor.fetchone()
    if tweet is None:
        abort(404)
    if tweet[1] != user_id:
        abort(401)

    query = "DELETE FROM tweet WHERE id=%(tweet_id)s;"
    params = {'tweet_id': tweet_id}
    cursor = g.db.cursor()
    cursor.execute(query, params)
    g.db.commit()
    return "", 204


@app.route('/profile/<username>')
def get_profile(username):
    query = """
        SELECT id, first_name, last_name, birth_date
        FROM twitter_user
        WHERE username = %(username)s;
    """
    cursor = g.db.cursor()
    cursor.execute(query, {'username': username})
    profile = cursor.fetchone()
    if profile is None:
        abort(404)

    user_id, first_name, last_name, birth_date = profile
    data = {
        "user_id": user_id,
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "birth_date": birth_date,
    }

    # fetch all user tweets
    query = """
        SELECT id, created, content
        FROM tweet
        WHERE user_id = %(user_id)s;
    """
    cursor = g.db.cursor()
    cursor.execute(query, {'user_id': user_id})
    data['tweet_count'] = 0
    data['tweets'] = []
    for tweet in cursor.fetchall():
        tweet_id, created, content = tweet
        data['tweets'].append({
            "id": tweet_id,
            "text": content,
            "date": python_date_to_json_str(sqlite_date_to_python(created)),
            "uri": '/tweet/{}'.format(tweet_id)
        })
        data['tweet_count'] += 1
    return json.dumps(data), 200, {'Content-Type': JSON_MIME_TYPE}


@app.route('/profile', methods=["POST"])
@json_only
@auth_only
def post_profile(user_id):
    for key in ['first_name', 'last_name', 'birth_date']:
        if key not in request.json:
            abort(400)

    query = """
        UPDATE twitter_user
        SET first_name=%(first_name)s, last_name=%(last_name)s,
        birth_date=%(birth_date)s;
    """
    params = {
        'first_name': request.json['first_name'],
        'last_name': request.json['last_name'],
        'birth_date': request.json['birth_date']
    }
    try:
        cursor = g.db.cursor()
        cursor.execute(query, params)
        g.db.commit()
    except sqlite3.IntegrityError:
        abort(500)
    else:
        return "", 202


@app.errorhandler(404)
def not_found(e):
    return "{}", 404, {'Content-Type': JSON_MIME_TYPE}


@app.errorhandler(401)
def not_authorized(e):
    return "{}", 401, {'Content-Type': JSON_MIME_TYPE}


@app.errorhandler(400)
def bad_request(e):
    return "{}", 400, {'Content-Type': JSON_MIME_TYPE}
