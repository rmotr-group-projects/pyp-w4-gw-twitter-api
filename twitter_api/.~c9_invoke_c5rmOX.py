import sqlite3

from flask import Flask
from flask import g
from utils import *
from flask import request

#from hashlib import md5 #  temporary until we review the py 2 / py 3 task
import json
import random, string

app = Flask(__name__)


def connect_db(db_name):
    return sqlite3.connect(db_name)
    
def _gen_access_token(user_id):
    token = ''.join(random.choice(string.ascii_uppercase + string.digits) for i in range(4))
    query = 'INSERT INTO "auth" (user_id, access_token) VALUES ("{}", "{}")'.format(user_id, token)
    g.db.execute(query)
    g.db.commit()
    return token
    
@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])


# implement your views here


@app.errorhandler(404)
def not_found(e):
    return '', 404


@app.errorhandler(401)
def unauth_request(e):
    return '', 401

        # If you type https://pyp-w4-gw-twitter-api-gobglobgrodgrob.c9users.io/login
def login():
    if request.method == 'POST':
        # import ipdb;  ipdb.set_trace()
        data = json.loads(request.data)
        # print md5( data['password']) 
        password =  md5(data['password']).hexdigest()# {u'username': u'demo', u'password': u'demo'} 
        cur = g.db.cursor()
        query = 'select id from user where username="{}" and password="{}";'.format(data['username'],password )
        # print command
        cur.execute(query)
        curresult = cur.fetchone()
        if not curresult:
            return "User login failed",401
        else:
            user_id = curresult[0]
            # token = _gen_access_token(user_id)
            
            return  json.dumps( {"access_token" : _gen_access_token(user_id) } ),200
            
        
        # print format(md5(data['password']).hexdigest()),data['password']
        return "Thanks!",200
    else:
        return "Please use Post",201 


@app.route('/logout', methods=['GET', 'POST']) 
def logout():        
    p