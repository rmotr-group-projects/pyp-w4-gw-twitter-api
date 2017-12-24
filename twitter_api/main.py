import sqlite3

from flask import Flask
from flask import g
import json
from .utils import (JSON_MIME_TYPE, python_date_to_json_str, sqlite_date_to_python)


app = Flask(__name__)


def connect_db(db_name):
    return sqlite3.connect(db_name)


@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])


@app.route('/tweet/<int:tweet_id>')
def get_tweet(tweet_id):

    query = """
        SELECT u.id, u.username, t.content, t.created
        FROM user u
        INNER JOIN tweet t
        ON u.id = t.id
        WHERE t.id=:tweet_id;"""

    cursor = g.db.execute(query, {'tweet_id': tweet_id})

    u_id, username, content, dt_created = cursor.fetchone()

    # implement error if id doesnt exist

    # FIX dt_created here !!! see how data is parsed in solutions !!!
    # what is the point of the python_date_to_json_str() and sqlite_date_to_python() functions???
    tweet_data = {
       'id': u_id,
       'content': content,
       'date': python_date_to_json_str(sqlite_date_to_python(dt_created)),
       'profile': '/profile/{}'.format(username),
       'uri': '/tweet/{}'.format(tweet_id)
    }

    content = json.dumps(tweet_data)

    return content, 200, {'Content-Type': JSON_MIME_TYPE}


@app.errorhandler(404)
def not_found(e):
    return '', 404


@app.errorhandler(401)
def not_found(e):
    return '', 401


def testing():
    print("hellow")


if __name__ == '__main__':
    testing()
