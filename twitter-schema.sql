-- sqlite3 database.db < twitter-schema.sql

PRAGMA foreign_keys = ON;

DROP TABLE if exists twitter_user;
CREATE TABLE twitter_user (
  id INTEGER PRIMARY KEY autoincrement,
  username TEXT NOT NULL,
  password TEXT NOT NULL,
  first_name TEXT,
  last_name TEXT,
  birth_date DATE,
  CHECK (
      length("birth_date") = 10
  )
);

DROP TABLE if exists tweet;
CREATE TABLE tweet (
  id INTEGER PRIMARY KEY autoincrement,
  user_id INTEGER,
  created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  content TEXT NOT NULL,
  FOREIGN KEY(user_id) REFERENCES twitter_user(id),
  CHECK(
      typeof("content") = "text" AND
      length("content") <= 140
  )
);

DROP TABLE if exists auth;
CREATE TABLE auth (
  id INTEGER PRIMARY KEY autoincrement,
  user_id INTEGER,
  access_token TEXT NOT NULL,
  created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES twitter_user(id)
);

CREATE UNIQUE INDEX auth_access_token_idx ON auth (access_token);
