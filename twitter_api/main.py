import sqlite3

from flask import Flask, g, abort, request
import json
from .utils import (JSON_MIME_TYPE, auth_only, json_only, python_date_to_json_str, sqlite_date_to_python)


app = Flask(__name__)


def connect_db(db_name):
    return sqlite3.connect(db_name)


@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])


@app.route('/tweet/<int:tweet_id>', methods=['GET'])
def get_tweet_user(tweet_id):

    query = """
        SELECT u.id, u.username, t.content, t.created
        FROM user u
        INNER JOIN tweet t
        ON u.id = t.id
        WHERE t.id=:tweet_id;"""

    # create a cursor object, which is similar to an iterator
    cursor = g.db.execute(query, {'tweet_id': tweet_id})

    # fetchone is much like the next() function applied to
    # an iterator
    tweet = cursor.fetchone()

    if tweet is None:
        abort(404)

    u_id, username, content, dt_created = tweet

    tweet_data = {
       'id': u_id,
       'content': content,
       'date': python_date_to_json_str(sqlite_date_to_python(dt_created)),
       'profile': '/profile/{}'.format(username),
       'uri': '/tweet/{}'.format(tweet_id)
    }

    content = json.dumps(tweet_data)

    return content, 200, {'Content-Type': JSON_MIME_TYPE}


@app.route('/tweet', methods=['POST'])
@json_only
@auth_only
def tweet_post(user_id):
    """
    Given a post request by the web client, check the access token of the user making the requests (made possible by the auth_only decorator) and if user has a valid access token, insert their post in the tweet database

    user_id is given by the auth_only decorator
    """
    if 'content' not in request.json:
        abort(400)

    insert_query = """
            INSERT INTO tweet ("user_id", "content")
            VALUES (:user_id, :content);
    """

    params = {
        'user_id': user_id,
        'content': request.json['content']
    }

    g.db.execute(insert_query, params)
    g.db.commit()

    return '', 201


@app.errorhandler(404)
def not_found(e):
    return '', 404
