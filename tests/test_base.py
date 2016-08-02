# -*- coding: utf-8 -*-
import os
import sqlite3
import unittest
import tempfile

from twitter_api import settings
from twitter_api import app
from twitter_api.main import connect_db
from twitter_api.utils import md5


class BaseTwitterAPITestCase(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'testing secret key'
        self.tmp_handle, self.tmp_name = tempfile.mkstemp()
        app.config['DATABASE'] = self.tmp_name

        # set up testing database
        db = connect_db(db_name=self.tmp_name)
        self.db = db
        self.load_fixtures()

        self.client = app.test_client()

    def tearDown(self):
        try:
            self.db.close()
        except sqlite3.OperationalError:
            pass
        os.remove(self.tmp_name)

    def load_fixtures(self):
        with open(os.path.join(settings.BASE_DIR, 'twitter-schema.sql'), 'r') as f:
            sql_query = f.read()
        for statement in sql_query.split(';'):
            self.db.execute(statement)

        self.db.execute('INSERT INTO "user" ("id", "username", "password", "first_name", "last_name", "birth_date") VALUES (1, "testuser1", "{}", "Test", "User", "2016-01-30");'.format(md5('user1-pass'.encode('utf-8')).hexdigest()))
        self.db.execute('INSERT INTO "user" ("id", "username", "password") VALUES (2, "testuser2", "{}");'.format(md5('1234'.encode('utf-8')).hexdigest()))
        self.db.execute('INSERT INTO "user" ("id", "username", "password") VALUES (3, "testuser3", "{}");'.format(md5('1234'.encode('utf-8')).hexdigest()))

        self.db.execute('INSERT INTO "tweet" ("id", "user_id", "content", "created") VALUES (1, 1, "Tweet 1 testuser1", "2016-06-01 05:13:00");')
        self.db.execute('INSERT INTO "tweet" ("id", "user_id", "content", "created") VALUES (2, 1, "Tweet 2 testuser1", "2016-06-01 05:22:00");')
        self.db.execute('INSERT INTO "tweet" ("id", "user_id", "content", "created") VALUES (3, 2, "Tweet 1 testuser2", "2016-06-01 05:38:00");')

        self.db.commit()


class AuthorizedTwitterAPITestCase(BaseTwitterAPITestCase):
    def setUp(self):
        super(AuthorizedTwitterAPITestCase, self).setUp()

        self.user1_token = 'AB$11'
        self.user2_token = 'AB$22'

        self.db.execute('INSERT INTO "auth" ("user_id", "access_token") VALUES (1, "%s");' % self.user1_token)
        self.db.execute('INSERT INTO "auth" ("user_id", "access_token") VALUES (2, "%s");' % self.user2_token)
        self.db.commit()
