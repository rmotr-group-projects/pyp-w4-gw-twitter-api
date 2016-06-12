# -*- coding: utf-8 -*-
import json

from ..test_base import AuthorizedTwitterAPITestCase


class TweetResource(AuthorizedTwitterAPITestCase):
    def test_get_tweet_by_id_successful(self):
        response = self.client.get('/tweet/1')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        data = json.loads(response.data.decode(response.charset))

        self.assertTrue('id' in data)
        self.assertTrue('content' in data)
        self.assertTrue('date' in data)
        self.assertTrue('profile' in data)
        self.assertTrue('uri' in data)

        self.assertEqual(data['id'], 1)
        self.assertEqual(data['content'], "Tweet 1 testuser1")
        self.assertEqual(data['date'], "2016-06-01 05:13:00")
        self.assertEqual(data['profile'], "/profile/testuser1")
        self.assertEqual(data['uri'], "/tweet/1")

    def test_get_tweet_by_id_doesnt_exist(self):
        response = self.client.get('/tweet/99')
        self.assertEqual(response.status_code, 404)

    def test_post_content_not_json(self):
        response = self.client.post('/tweet', data="junk",
                                    content_type='application/xml')
        self.assertEqual(response.status_code, 400)

    def test_post_tweet_successfully(self):
        # Preconditions
        cursor = self.db.execute("select * from tweet where user_id = 1;")
        self.assertEqual(len(cursor.fetchall()), 2)

        data = {
            "content": "API tweet test",
            "access_token": self.user1_token
        }
        response = self.client.post(
            '/tweet',
            data=json.dumps(data),
            content_type='application/json')

        self.assertEqual(response.status_code, 201)

        # Postconditions
        cursor = self.db.execute("select * from tweet where user_id = 1;")
        self.assertEqual(len(cursor.fetchall()), 3)

    def test_post_tweet_witout_token(self):
        # Preconditions
        cursor = self.db.execute("select * from tweet where user_id = 1;")
        self.assertEqual(len(cursor.fetchall()), 2)

        data = {
            "content": "API tweet test",
        }
        response = self.client.post(
            '/tweet',
            data=json.dumps(data),
            content_type='application/json')

        self.assertEqual(response.status_code, 401)

        # Postconditions
        cursor = self.db.execute("select * from tweet where user_id = 1;")
        self.assertEqual(len(cursor.fetchall()), 2)

    def test_post_tweet_invalid_access_token(self):
        # Preconditions
        cursor = self.db.execute("select * from tweet where user_id = 1;")
        self.assertEqual(len(cursor.fetchall()), 2)

        data = {
            "content": "API tweet test",
            'access_token': 'JUNK-999-XXX'
        }
        response = self.client.post(
            '/tweet',
            data=json.dumps(data),
            content_type='application/json')

        self.assertEqual(response.status_code, 401)

        # Postconditions
        cursor = self.db.execute("select * from tweet where user_id = 1;")
        self.assertEqual(len(cursor.fetchall()), 2)

    def test_delete_tweet_successful(self):
        # Preconditions
        cursor = self.db.execute("select * from tweet where user_id = 1;")
        self.assertEqual(len(cursor.fetchall()), 2)

        data = {
            'access_token': self.user1_token
        }
        response = self.client.delete(
            '/tweet/1',
            data=json.dumps(data),
            content_type='application/json')

        self.assertEqual(response.status_code, 204)

        # Postconditions
        cursor = self.db.execute("select * from tweet where user_id = 1;")
        self.assertEqual(len(cursor.fetchall()), 1)

        cursor = self.db.execute("select * from tweet where id = 1;")
        self.assertEqual(len(cursor.fetchall()), 0)

        cursor = self.db.execute("select * from tweet where id = 2;")
        self.assertEqual(len(cursor.fetchall()), 1)

    def test_delete_tweet_doesnt_belong_user(self):
        # Preconditions
        cursor = self.db.execute("select * from tweet where user_id = 1;")
        self.assertEqual(len(cursor.fetchall()), 2)

        data = {
            'access_token': self.user2_token
        }
        response = self.client.delete(
            '/tweet/1',
            data=json.dumps(data),
            content_type='application/json')

        self.assertEqual(response.status_code, 401)

        # Postconditions
        cursor = self.db.execute("select * from tweet where user_id = 1;")
        self.assertEqual(len(cursor.fetchall()), 2)

    def test_delete_tweet_invalid_token(self):
        # Preconditions
        cursor = self.db.execute("select * from tweet where user_id = 1;")
        self.assertEqual(len(cursor.fetchall()), 2)

        data = {
            'access_token': 'JUNK-999'
        }
        response = self.client.delete(
            '/tweet/1',
            data=json.dumps(data),
            content_type='application/json')

        self.assertEqual(response.status_code, 401)

        # Postconditions
        cursor = self.db.execute("select * from tweet where user_id = 1;")
        self.assertEqual(len(cursor.fetchall()), 2)

    def test_delete_tweet_doesnt_exist(self):
        # Preconditions
        cursor = self.db.execute("select * from tweet where user_id = 1;")
        self.assertEqual(len(cursor.fetchall()), 2)

        data = {
            'access_token': self.user1_token
        }
        response = self.client.delete(
            '/tweet/9999',
            data=json.dumps(data),
            content_type='application/json')

        self.assertEqual(response.status_code, 404)

        # Postconditions
        cursor = self.db.execute("select * from tweet where user_id = 1;")
        self.assertEqual(len(cursor.fetchall()), 2)
