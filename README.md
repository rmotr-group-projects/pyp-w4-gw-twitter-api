# [pyp-w4] Twitter API

For today's project, we're going to turn our previous Twitter clone into a RESTful API web service.

## Setting up the database

The data model remains the same. Check `twitter-schema.sql` for more details.

```bash
$ sqlite3 twitter.db < twitter-schema.sql
$ sqlite3 twitter.db < twitter-data.sql
```

# API overview

This is a simple RESTful API. All the data should be encoded as _json_.

## Endpoints

### Login Resource

```
POST /login
{
  "username": "demo",
  "password": "demo"
}
>>>
200 Ok
{
  "access_token": <ACCESS-TOKEN>
}
```

### Logout Resource

```
POST /logout
{
    "access_token": <ACCESS-TOKEN>
}
>>>
204 No Content
```

### Profile Resource

**Get public profile**

```
GET /profile/<USERNAME>
>>>
200 Ok
{
  "user_id": 1,
  "username": <USERNAME>,
  "first_name": "John",
  "last_name": "Doe",
  "birth_date": "2016-01-30",
  "tweets": [
    {
        "id": 38811,
        "text": "Tweet test",
        "date": "2016-06-01T05:13:00",
        "uri": "/tweet/38811"
    },
    {
        "id": 18832,
        "text": "Other tweet ",
        "date": "2016-06-01T05:22:00",
        "uri": "/tweet/18832"
    }
  ],
  "tweet_count": 2
}
```

**Update profile**

(Must be the authorized user. User resolved from token)

```
POST /profile
{
  "first_name": "John",
  "last_name": "Doe",
  "birth_date": "1980-12-31",
  "access_token": <ACCESS-TOKEN>
}
```
### Tweet Resource

**GET a tweet**

```
GET /tweet/<TWEET-ID>
>>>
200 Ok
{
  "id": <TWEET-ID>,
  "content": "Tweet test",
  "date": "2016-12-31T00:30:19",
  "profile": "/profile/<USERNAME>",
  "uri": "/tweet/<TWEET-ID>"
}
```

**Create a tweet**

(Must be the authorized user. User resolved from token)

```
POST /tweet
{
  "content": "Tweet test",
  "access_token": <ACCESS-TOKEN>
}
>>>
201 Created
```

**Delete a tweet**

(Must be the authorized user. User resolved from token)

```
DELETE /tweet/<TWEET-ID>
{
  "access_token": <ACCESS-TOKEN>
}
>>>
204 No Content
```


## Running the app server

```bash
$ python run_server.py
```
