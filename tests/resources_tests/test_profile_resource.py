# -*- coding: utf-8 -*-
import json

from ..test_base import AuthorizedTwitterAPITestCase


class ProfileResourceTestCase(AuthorizedTwitterAPITestCase):

    def test_get_profile_successful(self):
        response = self.client.get('/profile/testuser1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        data = json.loads(response.data.decode(response.charset))
        expected = {
            'user_id': 1,
            'username': 'testuser1',
            'first_name': 'Test',
            'last_name': 'User',
            'birth_date': '2016-01-30',
            'tweets': [
                {
                    'date': '2016-06-01T05:13:00',
                    'id': 1,
                    'text': 'Tweet 1 testuser1',
                    'uri': '/tweet/1'
                },
                {
                    'date': '2016-06-01T05:22:00',
                    'id': 2,
                    'text': 'Tweet 2 testuser1',
                    'uri': '/tweet/2'
                }
            ],
            'tweet_count': 2,
        }
        self.assertEqual(data, expected)

    def test_get_profile_does_not_exit(self):
        response = self.client.get('/profile/doesnotexist')
        self.assertEqual(response.status_code, 404)

    def test_get_profile_not_complete_data(self):
        response = self.client.get('/profile/testuser3')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        data = json.loads(response.data.decode(response.charset))
        expected = {
            'user_id': 3,
            'username': 'testuser3',
            'first_name': None,
            'last_name': None,
            'birth_date': None,
            'tweets': [],
            'tweet_count': 0,
        }
        self.assertEqual(data, expected)

    def test_post_profile_successfully(self):
        # Preconditions
        cursor = self.db.execute("select * from user where id = 1;")
        expected = (1, 'testuser1', '022c0b524a0258fc73d5ce9bcb0e5aa2',
                    'Test', 'User', '2016-01-30')
        self.assertEqual(cursor.fetchone(), expected)

        data = {
            "access_token": self.user1_token,
            "first_name": "New name",
            "last_name": "New last name",
            "birth_date": "1988-01-01",
        }
        response = self.client.post(
            '/profile',
            data=json.dumps(data),
            content_type='application/json')

        self.assertEqual(response.status_code, 201)

        # Postconditions
        cursor = self.db.execute("select * from user where id = 1;")
        expected = (1, 'testuser1', '022c0b524a0258fc73d5ce9bcb0e5aa2',
                    'New name', 'New last name', '1988-01-01')
        self.assertEqual(cursor.fetchone(), expected)

    def test_post_profile_missing_required_fields(self):
        # Preconditions
        cursor = self.db.execute("select * from user where id = 1;")
        expected = (1, 'testuser1', '022c0b524a0258fc73d5ce9bcb0e5aa2',
                    'Test', 'User', '2016-01-30')
        self.assertEqual(cursor.fetchone(), expected)

        data = {
            "access_token": self.user1_token,
            # missing first_name
            "last_name": "New last name",
            "birth_date": "1988-01-01",
        }
        response = self.client.post(
            '/profile',
            data=json.dumps(data),
            content_type='application/json')

        self.assertEqual(response.status_code, 400)

        # Postconditions (nothing changed)
        cursor = self.db.execute("select * from user where id = 1;")
        expected = (1, 'testuser1', '022c0b524a0258fc73d5ce9bcb0e5aa2',
                    'Test', 'User', '2016-01-30')
        self.assertEqual(cursor.fetchone(), expected)

    def test_post_profile_content_not_json(self):
        # Preconditions
        cursor = self.db.execute("select * from user where id = 1;")
        expected = (1, 'testuser1', '022c0b524a0258fc73d5ce9bcb0e5aa2',
                    'Test', 'User', '2016-01-30')
        self.assertEqual(cursor.fetchone(), expected)

        data = {
            "access_token": self.user1_token,
            # missing first_name
            "last_name": "New last name",
            "birth_date": "1988-01-01",
        }
        response = self.client.post(
            '/profile',
            data=json.dumps(data),
            content_type='application/xml')  # not JSON

        self.assertEqual(response.status_code, 400)

        # Postconditions (nothing changed)
        cursor = self.db.execute("select * from user where id = 1;")
        expected = (1, 'testuser1', '022c0b524a0258fc73d5ce9bcb0e5aa2',
                    'Test', 'User', '2016-01-30')
        self.assertEqual(cursor.fetchone(), expected)

    def test_post_profile_missing_access_token(self):
        # Preconditions
        cursor = self.db.execute("select * from user where id = 1;")
        expected = (1, 'testuser1', '022c0b524a0258fc73d5ce9bcb0e5aa2',
                    'Test', 'User', '2016-01-30')
        self.assertEqual(cursor.fetchone(), expected)

        data = {
            # missing access token
            "first_name": "New name",
            "last_name": "New last name",
            "birth_date": "1988-01-01",
        }
        response = self.client.post(
            '/profile',
            data=json.dumps(data),
            content_type='application/json')

        self.assertEqual(response.status_code, 401)

        # Postconditions (nothing changed)
        cursor = self.db.execute("select * from user where id = 1;")
        expected = (1, 'testuser1', '022c0b524a0258fc73d5ce9bcb0e5aa2',
                    'Test', 'User', '2016-01-30')
        self.assertEqual(cursor.fetchone(), expected)

    def test_post_profile_invalid_access_token(self):
        # Preconditions
        cursor = self.db.execute("select * from user where id = 1;")
        expected = (1, 'testuser1', '022c0b524a0258fc73d5ce9bcb0e5aa2',
                    'Test', 'User', '2016-01-30')
        self.assertEqual(cursor.fetchone(), expected)

        data = {
            "access_token": "this-is-not-valid",
            "first_name": "New name",
            "last_name": "New last name",
            "birth_date": "1988-01-01",
        }
        response = self.client.post(
            '/profile',
            data=json.dumps(data),
            content_type='application/json')

        self.assertEqual(response.status_code, 401)

        # Postconditions (nothing changed)
        cursor = self.db.execute("select * from user where id = 1;")
        expected = (1, 'testuser1', '022c0b524a0258fc73d5ce9bcb0e5aa2',
                    'Test', 'User', '2016-01-30')
        self.assertEqual(cursor.fetchone(), expected)
