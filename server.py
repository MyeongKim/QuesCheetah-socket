import socketio
import eventlet
from flask import Flask
import redis

import urllib.request, urllib.error, urllib.parse
import json
from urllib.error import HTTPError

from datetime import datetime

# from request import getdata
sio = socketio.Server()
app = Flask(__name__)

r = redis.StrictRedis(host='localhost', port=6379, db=0)

def getdata(question_id, api_key):
    # request to rest api
    url = 'http://127.0.0.1:8000/v1/questions/'+str(question_id)+'/SimpleResult'
    req = urllib.request.Request(url)
    req.add_header('api-key', api_key)

    try:
        response_json = urllib.request.urlopen(req).read()
        response_json = json.loads(response_json.decode('utf-8'))
    except HTTPError:
        print(HTTPError.reason)
        return {'error': 'true', 'desc': 'Socket server failed to get data from api server.'}

    print(response_json)

    return response_json

@app.route('/')
def index():
    return 'Hello World!'

@sio.on('connect')
def connect(sid, environ):
    print('connect ', sid)
    r.set(sid, datetime.now())

@sio.on('send')
def message(sid, data):
    print('message ', data)

    # enter question_id room
    sio.enter_room(sid, data['question_id'])
    r.sadd(data['question_id'], sid)

    # rooms
    r.sadd('questions', data['question_id'])

    # get data from this questin_id
    response = getdata(data['question_id'], data['api-key'])

    # return full response data to send client
    sio.emit('reply', response, room=sid)

    # return partial response data to room
    sio.emit('reply', data, room=data['question_id'], skip_sid=sid)

    r.set(sid, datetime.now())

@sio.on('disconnect')
def disconnect(sid):
    print('disconnect ', sid)

    # Delete client time info
    r.delete(sid)

    # Delete client question info
    for s in r.smembers('questions'):
        r.srem(s, sid)
        if not r.smembers(s):
            print(s,"is empty")
            r.srem('questions', s)
            # r.delete(s)

if __name__ == '__main__':
    # wrap Flask application with socketio's middleware
    app = socketio.Middleware(sio, app)

    # deploy as an eventlet WSGI server
    eventlet.wsgi.server(eventlet.listen(('127.0.0.1', 5000)), app)
