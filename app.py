import logging
import os

from flask import Flask, session
from flask_socketio import SocketIO, emit

import config
from microflack_common import requests

logging.basicConfig(level=os.environ.get('LOG_LEVEL', logging.WARNING))

app = Flask(__name__)
config_name = os.environ.get('FLASK_CONFIG', 'dev')
app.config.from_object(getattr(config, config_name.title() + 'Config'))

message_queue = 'redis://' + os.environ['REDIS'] if 'REDIS' in os.environ \
    else None
socketio = SocketIO(app, message_queue=message_queue)


@socketio.on('ping_user')
def on_ping_user(token):
    """Clients must send this event periodically to keep the user online."""
    rv = requests.put('/api/users/me',
                      headers={'Authorization': 'Bearer ' + token},
                      raise_for_status=False)
    if rv.status_code != 401:
        session['token'] = token  # save token, disconnect() might need it
    else:
        emit('expired_token')


@socketio.on('post_message')
def on_post_message(data, token):
    """Clients send this event to when the user posts a message."""
    rv = requests.post('/api/messages', json=data,
                       headers={'Authorization': 'Bearer ' + token},
                       raise_for_status=False)
    if rv.status_code != 401:
        session['token'] = token  # save token, disconnect() might need it
    else:
        emit('expired_token')


@socketio.on('disconnect')
def on_disconnect():
    """A Socket.IO client has disconnected. If we know who the user is, then
    update our state accordingly.
    """
    if 'token' in session:
        requests.delete(
            '/api/users/me',
            headers={'Authorization': 'Bearer ' + session['token']},
            raise_for_status=False)


if __name__ == '__main__':
    socketio.run(app)
