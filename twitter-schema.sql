DROP TABLE if exists twitter_user;
CREATE TABLE twitter_user (
  id serial PRIMARY KEY,
  username TEXT NOT NULL,
  password TEXT NOT NULL,
  first_name TEXT,
  last_name TEXT,
  birth_date DATE
);

DROP TABLE if exists tweet;
CREATE TABLE tweet (
  id serial PRIMARY KEY,
  user_id INTEGER REFERENCES twitter_user(id),
  created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  content TEXT NOT NULL
);

DROP TABLE if exists auth;
CREATE TABLE auth (
  id serial PRIMARY KEY,
  user_id INTEGER REFERENCES twitter_user(id),
  access_token TEXT NOT NULL,
  created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX auth_access_token_idx ON auth (access_token);
