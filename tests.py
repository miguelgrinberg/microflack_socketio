#!/usr/bin/env python
import os
os.environ['FLASK_CONFIG'] = 'test'

import mock
import os
import unittest

from microflack_common.auth import generate_token
from microflack_common.test import FlackTestCase

from app import app, socketio


class SocketIOTests(FlackTestCase):
    def setUp(self):
        self.ctx = app.app_context()
        self.ctx.push()
        self.client = socketio.test_client(app)

    def tearDown(self):
        self.ctx.pop()

    @mock.patch('app.requests')
    def test_socketio(self, requests):
        token = generate_token(1)

        # clear old socket.io notifications
        self.client.get_received()

        # ping user via socketio to make it be back online
        requests.put.return_value.status_code = 200
        self.client.emit('ping_user', token)
        requests.put.assert_called_with(
            '/api/users/me', headers={'Authorization': 'Bearer ' + token},
            raise_for_status=False)
        self.assertEqual(self.client.get_received(), [])

        # same as above, but with bad token
        requests.put.return_value.status_code = 401
        self.client.emit('ping_user', 'bar')
        requests.put.assert_called_with(
            '/api/users/me', headers={'Authorization': 'Bearer ' + 'bar'},
            raise_for_status=False)
        self.assertEqual(
            self.client.get_received(),
            [{'name': 'expired_token', 'args': [None], 'namespace': '/'}])

        # post a message via socketio
        requests.post.return_value.status_code = 200
        self.client.emit('post_message', {'source': 'foo'}, token)
        requests.post.assert_called_with(
            '/api/messages', json={'source': 'foo'},
            headers={'Authorization': 'Bearer ' + token},
            raise_for_status=False)
        self.assertEqual(self.client.get_received(), [])

        # same as above, but with bad token
        requests.post.return_value.status_code = 401
        self.client.emit('post_message', {'source': 'foo'}, 'bar')
        requests.post.assert_called_with(
            '/api/messages', json={'source': 'foo'},
            headers={'Authorization': 'Bearer ' + 'bar'},
            raise_for_status=False)
        self.assertEqual(
            self.client.get_received(),
            [{'name': 'expired_token', 'args': [None], 'namespace': '/'}])

        # disconnect the user
        self.client.disconnect()
        requests.delete.assert_called_with(
            '/api/users/me', headers={'Authorization': 'Bearer ' + token},
            raise_for_status=False)

        # same as above, but with bad token
        self.client.disconnect()
        requests.delete.assert_called_with(
            '/api/users/me', headers={'Authorization': 'Bearer ' + token},
            raise_for_status=False)


if __name__ == '__main__':
    unittest.main(verbosity=2)
