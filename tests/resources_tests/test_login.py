# -*- coding: utf-8 -*-
import json

from ..test_base import BaseTwitterAPITestCase


class LoginResourceTestCase(BaseTwitterAPITestCase):
    def test_login_successful(self):
        # Precondition
        cursor = self.db.execute("select * from auth;")
        self.assertEqual(len(cursor.fetchall()), 1)

        data = {
            "username": "testuser1",
            "password": "user1-pass"
        }

        response = self.client.post(
            '/login',
            data=json.dumps(data),
            content_type='application/json')

        self.assertEqual(response.status_code, 201)

        data = json.loads(response.data.decode(response.charset))
        self.assertTrue('access_token' in data)
        access_token = data['access_token']

        # Postconditions
        cursor = self.db.execute("select * from auth;")
        self.assertEqual(len(cursor.fetchall()), 2)

        cursor = self.db.execute("select user_id, access_token from auth WHERE access_token=:access_token;", {'access_token': access_token})
        auth_obj = cursor.fetchone()
        self.assertIsNotNone(auth_obj)
        user_id, token = auth_obj
        self.assertEqual(user_id, 1)
        self.assertEqual(token, access_token)

    def test_login_missing_password(self):
        # Precondition
        cursor = self.db.execute("select * from auth;")
        self.assertEqual(len(cursor.fetchall()), 1)

        data = {
            "username": "testuser1"
        }

        response = self.client.post(
            '/login',
            data=json.dumps(data),
            content_type='application/json')

        self.assertEqual(response.status_code, 400)

        # Postconditions
        cursor = self.db.execute("select * from auth;")
        self.assertEqual(len(cursor.fetchall()), 1)

    def test_login_wrong_password(self):
        # Precondition
        cursor = self.db.execute("select * from auth;")
        self.assertEqual(len(cursor.fetchall()), 1)

        data = {
            "username": "testuser1",
            "password": "JUNK"
        }

        response = self.client.post(
            '/login',
            data=json.dumps(data),
            content_type='application/json')

        self.assertEqual(response.status_code, 401)

        # Postconditions
        cursor = self.db.execute("select * from auth;")
        self.assertEqual(len(cursor.fetchall()), 1)

    def test_login_username_doesnt_exist(self):
        # Precondition
        cursor = self.db.execute("select * from auth;")
        self.assertEqual(len(cursor.fetchall()), 1)

        data = {
            "username": "JUNK-1",
            "password": "user1-pass"
        }

        response = self.client.post(
            '/login',
            data=json.dumps(data),
            content_type='application/json')

        self.assertEqual(response.status_code, 404)

        # Postconditions
        cursor = self.db.execute("select * from auth;")
        self.assertEqual(len(cursor.fetchall()), 1)

    def test_login_already_has_token(self):
        # Precondition
        cursor = self.db.execute("select * from auth;")
        self.assertEqual(len(cursor.fetchall()), 1)

        data = {
            "username": "tokenUSER",
            "password": "1234"
        }

        response = self.client.post(
            '/login',
            data=json.dumps(data),
            content_type='application/json')

        self.assertEqual(response.status_code, 200)

        # Postconditions
        cursor = self.db.execute("select * from auth;")
        self.assertEqual(len(cursor.fetchall()), 1)
