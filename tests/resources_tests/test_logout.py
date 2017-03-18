# -*- coding: utf-8 -*-
import json

from ..test_base import AuthorizedTwitterAPITestCase


class LogoutTestCase(AuthorizedTwitterAPITestCase):

    def test_logout_successful(self):
        # Preconditions
        cursor = self.db.execute("select * from auth where user_id = 1;")
        self.assertIsNotNone(cursor.fetchone())

        response = self.client.post(
            '/logout',
            data=json.dumps({"access_token": self.user1_token}),
            content_type='application/json')

        self.assertEqual(response.status_code, 204)

        # Postconditions
        cursor = self.db.execute("select * from auth where user_id = 1;")
        self.assertIsNone(cursor.fetchone())

    def test_logout_missing_access_token(self):
        # Preconditions
        cursor = self.db.execute("select * from auth where user_id = 1;")
        self.assertIsNotNone(cursor.fetchone())
        response = self.client.post(
            '/logout',
            data=json.dumps({}),  # missing access_token
            content_type='application/json')
        #import pdb
        #pdb.set_trace()
        self.assertEqual(response.status_code, 401)

        # Postconditions
        cursor = self.db.execute("select * from auth where user_id = 1;")
        self.assertIsNotNone(cursor.fetchone())
