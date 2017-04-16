import sqlite3

from flask import Flask
from flask import g, request, abort, jsonify, make_response
from utils import json_only, auth_only, md5
from datetime import datetime
import json

app = Flask(__name__)


def connect_db(db_name):
    return sqlite3.connect(db_name)

    
@app.before_request
def before_request():
    g.db = connect_db(app.config['DATABASE'])


# implement your views here
@app.route('/login', methods=['POST'])
@json_only
def login():
    json_data = request.get_json()
    username = json_data.get('username', None)
    password = json_data.get('password', None)
    
    if not username:
        abort(400)
        
    elif not password:
        abort (400)
    
    else:
        # Check username is in the user's table
        user_query = g.db.execute("SELECT id, username, password FROM user WHERE username=:username",
                         {'username': username})
        
        user = user_query.fetchone()
        if user:
            hashed_password =  md5(password).hexdigest()
            id, username, db_password = user
            
            if hashed_password == db_password:
                access_token = str(md5(str(password) + '123'))
                
                query = 'INSERT INTO auth ("user_id", "access_token") VALUES (:user_id, :access_token);'
                params = {'user_id': id, 'access_token': access_token}
                try:
                    g.db.execute(query, params)
                    g.db.commit()
                
                except sqlite3.IntegrityError:
                    print ("Sorry, something went wrong")
                
                response = jsonify({'access_token': access_token})
                response.status_code = 201
                
                # Alternative way to return custom status code
                # return make_response(jsonify(response), 201)
                
                return response
                
            else:
                abort(401)
        else:
            abort(404)
    
@app.route('/logout', methods=['POST'])
@auth_only
@json_only
def logout(user_id):
    json_data = request.get_json()
    access_token = json_data.get('access_token', None)
    
    query = "DELETE FROM auth WHERE user_id=:user_id;"
    params = {'user_id': user_id}
    
    try:
        g.db.execute(query, params)
        g.db.commit()
    except sqlite3.IntegrityError:
        print ("Ooops something went terribly wrong!")

    response = jsonify({"access_token": access_token})
    response.status_code = 204
    return response
    
    
@app.route('/profile/<username>', methods=['GET'])
def get_profile(username):
    user_query = g.db.execute("SELECT * FROM user WHERE username=:username",
                         {'username': username})
    user = user_query.fetchone()
    
    if user:
        id, username, password, first_name, last_name, birth_date = user
        
        tweets_query = g.db.execute("SELECT * FROM tweet WHERE user_id=:user_id", {'user_id': id})
        
        tweets = [dict(id=row[0], date=datetime.strptime(row[2], "%Y-%m-%d %H:%M:%S").isoformat(), text=row[3], uri= '/tweet/'+ str(row[0]))
              for row in tweets_query.fetchall()]
            
        tweet_count = len(tweets)
            
        data = {"user_id": id,
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "birth_date": birth_date,
                "tweets": tweets,
                "tweet_count": tweet_count}
        
        response = jsonify(data)
        return response
        
    else:
        abort(404)



@app.route('/profile', methods=['POST'])
@json_only
@auth_only
def update_profile(user_id):
    json_data = request.get_json()
    
    first_name = json_data.get('first_name', None)
    last_name = json_data.get('last_name', None)
    birth_date = json_data.get('birth_date', None)
    
    if first_name is None or last_name is None or birth_date is None:
        abort(400)
    
    query = "UPDATE user SET first_name=:first_name, last_name=:last_name, birth_date=:birth_date;"
    params = {'first_name':first_name, 'last_name':last_name, 'birth_date':birth_date}
    
    try:
        g.db.execute(query, params)
        g.db.commit()
    except sqlite3.IntegrityError:
        print ("Ooops something went terribly wrong!")
    
    return "Successfully Updated", 201


@app.route('/tweet/<tweet_id>', methods=['GET'])
def get_tweet(tweet_id):
    cursor = g.db.execute("SELECT id, user_id, created, content  FROM tweet WHERE id=:tweet_id", {'tweet_id': tweet_id})
    tweet = cursor.fetchone()
    
    if tweet:
        id, user_id, date, content = tweet
        
        user_query = g.db.execute("SELECT username FROM user WHERE id=:user_id", {'user_id': user_id})
        
        username = user_query.fetchone()[0]
        
        data = {
          "id": id,
          "content": content,
          "date": datetime.strptime(date, "%Y-%m-%d %H:%M:%S").isoformat(),
          "profile": "/profile/" + str(username),
          "uri": "/tweet/" + str(id)
            
        }
        
        return jsonify(data)
    else:
        abort(404)
    
    
@app.route('/tweet', methods=['POST'])
@json_only
@auth_only
def post_tweet(user_id):
    json_data = request.get_json()
    content = json_data.get('content', None)
    
    if not content:
        abort(400)
    else:
        query = 'INSERT INTO tweet ("user_id", "content") VALUES (:user_id, :content);'
        params = {'user_id': user_id, 'content': content}
        try:
            g.db.execute(query, params)
            g.db.commit()
        except sqlite3.IntegrityError:
            print("Oops error occurred")
            
        response = jsonify({})
        response.status_code = 201
            
        return response
            

@app.route('/tweet/<tweet_id>', methods=['DELETE'])
@json_only
@auth_only
def delete_tweet(user_id, tweet_id):
    cursor = g.db.execute("""SELECT user_id FROM tweet WHERE id=:tweet_id""",
                            {'tweet_id': tweet_id})
    tweet = cursor.fetchone()
    
    if tweet:
        id = tweet[0]
        if id != user_id:
            abort(401)
        else:
            try:
                g.db.execute("DELETE FROM tweet WHERE id=:tweet_id", {'tweet_id': tweet_id})
                g.db.commit()
            except sqlite3.IntegrityError:
                print ("Ooops something went wrong!")
            
            response = jsonify({})
            response.status_code = 204
                    
            return response 
    else:
        abort(404)
        
    

@app.errorhandler(404)
def not_found(e):
    return '', 404


@app.errorhandler(401)
def not_found(e):
    return '', 401


