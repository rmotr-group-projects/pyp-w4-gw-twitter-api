import json
import sqlite3
import datetime
from uuid import uuid4
from .utils import JSON_MIME_TYPE, md5, json_only, auth_only

from flask import Flask, Response, abort, request, g

app = Flask(__name__)


def connect_db(db_name):
    return sqlite3.connect(db_name)


@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])
    # Added row_factory here
    g.db.row_factory = sqlite3.Row


@app.route("/tweet/<int:TWEET_ID>", methods=['GET','DELETE'])
@auth_only
def get_tweet(TWEET_ID):
    # This is outside the if request.method because it is used in both codes.
    query = """
    SELECT
        t.id as id, u.username as profile, t.created as date,
        t.content as content, a.access_token as access_token
    FROM
        tweet t
    NATURAL INNER JOIN
        user u
    INNER JOIN 
        auth a
    ON 
        a.user_id = u.id
    WHERE
        t.id == '{}'
    """
    tweet_cursor = g.db.execute(query.format(TWEET_ID))
    # This will return None if the 0 items in the query
    tweet_fetch = tweet_cursor.fetchone()

    if not tweet_fetch:
        abort(404)
    tweet_dict = dict(tweet_fetch)
    if  request.method == 'GET':   
        tweet_dict['uri'] = '/tweet/{}'.format(TWEET_ID)
        tweet_dict['profile'] = '/profile/{}'.format(tweet_dict['profile'])
        time = datetime.datetime.strptime(tweet_dict['date'], '%Y-%m-%d %H:%M:%S')
        tweet_dict['date'] = time.strftime('%Y-%m-%dT%H:%M:%S')
        tweet_json = json.dumps(tweet_dict)
        return tweet_json, 200, {'Content-Type': JSON_MIME_TYPE}
    elif request.method == 'DELETE':
        request_info = request.json
        if request_info['access_token'] != tweet_dict['access_token']:
            abort(401)
        delete_query = """
        DELETE
        FROM
            tweet
        WHERE
            id == :id
        """
        g.db.execute(delete_query,tweet_dict)
        g.db.commit()
        return '',204

@app.route("/tweet", methods=['POST'])
@json_only
@auth_only
def post_tweet():
    post_data = request.json
    check_auth_query = """
    SELECT 
        user_id
    FROM
        auth
    WHERE
        access_token == :access_token
    """
    auth_check = g.db.execute(check_auth_query,
                               {'access_token':post_data['access_token']})
    auth_fetch = auth_check.fetchone()
    if not auth_fetch:
        abort(401)
    current_time = datetime.datetime.now()
    post_dict = dict(auth_fetch)
    post_dict['content'] = post_data['content']
    post_dict['created'] = current_time.strftime('%Y-%m-%d %H:%M:%S')
    post_query ="""
    INSERT INTO
        tweet(user_id, created, content)
    VALUES(
    :user_id, :created, :content
    );
    """
    g.db.execute(post_query,post_dict)
    g.db.commit()
    return '', 201

@app.route("/profile/<username>",methods=['GET'])
def get_profile(username):
    query = """
    SELECT
        u.id as user_id, u.username as username,
        u.first_name as first_name, u.last_name as last_name,
        u.birth_date as birth_date
    FROM
        user u
    WHERE
        u.username == '{}'
    """
    profile_cursor = g.db.execute(query.format(username))
    profile_fetch = profile_cursor.fetchone()
    if not profile_fetch:
        abort(404)
    profile_dict = dict(profile_fetch)
    profile_dict['tweet_count'] = 0
    tweet_query = """
    SELECT
        t.created as date, t.id as id, t.content as text
    FROM
        tweet t
    NATURAL JOIN
        user
    WHERE
        t.user_id = '{}'
    """
    tweets_cursor = g.db.execute(tweet_query.format(profile_dict['user_id']))
    tweet_fetch = [dict(tweet) for tweet in tweets_cursor.fetchall()]
    for tweet_dict in tweet_fetch:
        profile_dict['tweet_count'] += 1
        tweet_dict['uri'] = '/tweet/{}'.format(tweet_dict['id'])
        time = datetime.datetime.strptime(tweet_dict['date'],
                                          '%Y-%m-%d %H:%M:%S')
        tweet_dict['date'] = time.strftime('%Y-%m-%dT%H:%M:%S')

    profile_dict['tweets'] = tweet_fetch
    profile_json = json.dumps(profile_dict)
    return profile_json, 200, {'Content-Type': JSON_MIME_TYPE}


@app.route("/profile", methods=['POST'])
@json_only
@auth_only
def post_profile():
    list_of_required = ['access_token', 'first_name',
                                      'last_name','birth_date']
    profile_update = request.json
    if not all([True if key in profile_update
                else False for key in list_of_required]):
        abort(400)
    profile_query = """
    SELECT
        u.id as id
    FROM
        auth a
    NATURAL INNER JOIN
        user u
    WHERE
        a.access_token = :access_token
    """
    profile_access_check = g.db.execute(profile_query, profile_update)
    profile_fetch = profile_access_check.fetchone()
    if not profile_fetch:
        abort(401)
    profile_update.update(dict(profile_fetch))
    update_query ="""
    UPDATE
        user
    SET
        first_name == :first_name,
        last_name == :last_name,
        birth_date == :birth_date
    WHERE
        id = :id
    """
    g.db.execute(update_query, profile_update)
    g.db.commit()
    return '',202


@app.route("/login", methods=['POST'])
def login():
    # Request the POST from user
    user_data = request.json
    # Retrieve username and password if sent else return HTTP 400 error
    username = user_data['username']
    if 'password' not in user_data:
        abort(400)
    # Here we retrieve the password but only deal with it hashed
    password = md5(str.encode(user_data['password'], 'utf-8')).hexdigest()
    # We do an initial query to check if the user exist and to extract
    # user_id and password for another query and password confirmation
    does_user_exist = """
    SELECT
        u.id as user_id, u.password as password
    FROM
        user as u
    WHERE
        u.username == :username
    """

    user_exist = g.db.execute(does_user_exist, {'username': username,
                                                'password': password})
    user_fetch = user_exist.fetchone()
    # If user_fetch returns None bring up 404
    if not user_fetch:
        abort(404)

    # Dictionary conversion
    user_auth = dict(user_fetch)
    # We both remove and return the password element and check if it is correct
    if user_auth.pop('password') != password:
        abort(401)

    insert_query = """
    INSERT INTO auth (
        user_id, access_token)
    VALUES (
        :user_id,:access_token);
    """
    # Creating a uniqe access_token and storing it in the user_auth dictionary
    user_auth['access_token'] = uuid4().hex
    # Sending the query and commiting it to the database
    g.db.execute(insert_query, user_auth)
    g.db.commit()
    # converting the user_auth dict to json
    auth_json = json.dumps(user_auth)
    # submitting response to user can also use make_response() or Resopnse()
    # all three take data, HTTP Status Code, Content-Type as dictionary
    return auth_json, 201, {'Content-Type': JSON_MIME_TYPE}


@app.route("/logout", methods=['POST'])
@auth_only
def logout():
    user_passed_data = request.json
    delete_query= """
    DELETE
    FROM
        auth
    WHERE
        access_token = :access_token
    """
    g.db.execute(delete_query, user_passed_data)
    g.db.commit()
    return '', 204, {'Content-Type': JSON_MIME_TYPE}

@app.errorhandler(404)
def not_found(e):
    return '', 404


@app.errorhandler(401)
def not_found(e):
    return '', 401
