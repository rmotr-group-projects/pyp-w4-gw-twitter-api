import sqlite3
import random
import string

from flask import Flask
from flask import g

from utils import *

app = Flask(__name__)


def connect_db(db_name):
    return sqlite3.connect(db_name)


@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])


def create_token():
    characters = [ n for n in string.ascii_letters + string.digits]
    return "".join([random.choice(characters) for n in range(16)])


@app.route('/login', methods = ['POST'])
def login(username, password):
    # check the input, define if password is empty
    # check to see if user exists
    # get the password, missing pw: 400, wrong pw: 401
    # check equality
    # if user does not exist, error 404
    # return if successful 201
    pass

@app.route('/profile', methods = ['POST'])
#@auth_only() will return 401
#@json.only will return 400
def profile():
    #UPDATE OWN PROFILE
    # get the auth token so we know who to update
    # validate required fields - first name is req, if not exist return 400
    # update db with new values and return 201
    pass
    
@app.route('/profile/<USERNAME>')
def get_profile(username):
    #VIEW OTHER PROFILE
    # return 200 and json profile if profile exists
    # return 404 if no profile exists
    # generate an empty json list with defaults None
    pass



    #return 201
# @auth.only
#CREATE TWEET
def create_tweet():
    pass

#DELETE and VIEW tweets
@app.route('/tweet/<TWEET-ID>', methods = ["DELETE", "GET"])
def handle_tweet(tweet_id):
    #if delete:
    #    delete_tweet(tweet_id)
    #if get:
    #    get_tweet(tweet_id)
    pass
#DELETE TWEET
def delete_tweet(tweet_id):
    pass
#VIEW TWEET
def get_tweet(tweet_id):
    pass


@app.rof not ute('/logout', methods =['POST'])
def logout(access_token):
    #check if user is logged in (token)
    #cursor = self.db.execute("select * from auth where user_id = ?")
    #if no fetch result, return 401
    #else return 201 and delete from auth
    pass

@app.errorhandler(404)
def not_found(e):
    return '', 404


@app.errorhandler(401)
def not_found(e):
    return '', 401
