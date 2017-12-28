import sqlite3

from flask import Flask, g, abort, request
import json
from .utils import (JSON_MIME_TYPE, auth_only, json_only, python_date_to_json_str, sqlite_date_to_python, md5, generate_random_token)


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
        ON u.id = t.user_id
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
    # if 'content' not in request.json:
    #     abort(400)

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


@app.route('/tweet/<int:tweet_id>', methods=['DELETE'])
@auth_only
def tweet_delete(user_id, tweet_id):

    param = {'tweet_id': tweet_id}

    # check if tweet exists (if not, abort with status code 404)
    check_query = """
            SELECT id, user_id FROM tweet
            WHERE id=:tweet_id;
    """
    cursor = g.db.execute(check_query, param)

    tweet = cursor.fetchone()

    if not tweet:
        abort(404)

    if tweet[1] != user_id:
        abort(401)

    # if tweet exists, delete it
    delete_query = """
            DELETE FROM tweet
            WHERE tweet.id=:tweet_id
    """
    g.db.execute(delete_query, param)
    g.db.commit()

    return '', 204


@app.route('/profile/<username>')
def get_profile(username):

    # check if user exists
    check_query = """
            SELECT *
            FROM user u
            WHERE u.username=:username;
    """
    check_cursor = g.db.execute(check_query, {'username': username})

    if not check_cursor.fetchone():
        abort(404)

    # get data if user exists
    query = """
        SELECT
            u.id, u.username, u.first_name, u.last_name, u.birth_date,
            t.created, t.id, t.content
        FROM user u
        LEFT JOIN tweet t
        ON u.id = t.user_id
        WHERE u.username=:username;
    """

    cursor = g.db.execute(query, {'username': username})

    tweet = cursor.fetchall()

    # get tweet data
    tweets = [
        {
            'date': python_date_to_json_str(sqlite_date_to_python(t[-3])),
            'id': t[-2],
            'text': t[-1],
            'uri': '/tweet/{0}'.format(t[-2])
        }
        for t in tweet
        if all([t[-3], t[-2], t[-1]])  # include in list if all tweet data are nonempty
        ]

    # create profile data
    profile_data = {
        'user_id': tweet[0][0],
        'username': tweet[0][1],
        'first_name': tweet[0][2],
        'last_name': tweet[0][3],
        'birth_date': tweet[0][4],
        'tweets': tweets,
        'tweet_count': len(tweets),
    }

    content = json.dumps(profile_data)

    return content, 200, {'Content-Type': JSON_MIME_TYPE}


@app.route('/profile', methods=['POST'])
@json_only
@auth_only
def post_profile(user_id):

    update_query = """
            UPDATE user
            SET
                first_name=:first_name,
                last_name=:last_name,
                birth_date=:birth_date
            WHERE id=:user_id;
    """

    # check that required user info are provided
    for key in ['first_name', 'last_name', 'birth_date']:
        if key not in request.json:
            abort(400)

    params = {
        'first_name': request.json['first_name'],
        'last_name': request.json['last_name'],
        'birth_date': request.json['birth_date'],
        'user_id': user_id
    }

    g.db.execute(update_query, params)
    g.db.commit()

    return '', 202


@app.route('/login', methods=['POST'])
def login():

    # check if username exists
    check_username_query = """
            SELECT u.id, u.username FROM user u
            WHERE u.username=:username;
    """

    check_username_cursor = g.db.execute(check_username_query, {'username': request.json['username']})

    user_info = check_username_cursor.fetchone()

    if user_info is None:
        abort(404)

    # check if password is missing
    if 'password' not in request.json:
        abort(400)

    # check if password is correct
    password_hashed = md5(request.json['password']).hexdigest()
    check_password_query = """
            SELECT u.password FROM user u
            WHERE u.password=:password_hashed;
    """

    check_password_cursor = g.db.execute(check_password_query, {'password_hashed': password_hashed})

    password_hashed = check_password_cursor.fetchone()

    if password_hashed is None:
        abort(401)

    # if user exists and password is valid, generate access token
    # insert or replace it in the auth table, then return it to user
    new_access_token = generate_random_token()

    insert_access_token_query = """
            INSERT OR REPLACE INTO auth ("user_id", "access_token")
            VALUES (:user_id, :access_token);
    """

    params = {
        'user_id': user_info[0],
        'access_token': new_access_token
        }

    g.db.execute(insert_access_token_query, params)
    g.db.commit()

    # return access token
    access_token_cursor = g.db.execute("SELECT a.access_token FROM auth a WHERE a.user_id=:user_id;", {"user_id": user_info[0]})
    access_token_json = {
        'access_token': access_token_cursor.fetchone()[0]
    }

    return json.dumps(access_token_json), 201


@app.route('/logout', methods=['POST'])
@auth_only
def logout(user_id):
    delete_query = """
            DELETE FROM auth
            WHERE user_id=:user_id
    """

    g.db.execute(delete_query, {'user_id': user_id})
    g.db.commit()

    return '', 204


@app.errorhandler(404)
def not_found(e):
    return '', 404
