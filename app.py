# from flask import Flask, request, jsonify
# from markupsafe import escape
# from pathlib import Path
from ruamel.yaml import YAML
import uuid
import time
import hashlib
import logging
import logging.config
import os

from flask import Flask
from flask_restful import reqparse, abort, Api, Resource

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
# fh = logging.handlers.RotatingFileHandler(
#     filename=str(Path.home())+'/.micado-cli/micado-cli.log', mode='a', maxBytes=52428800, backupCount=3)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s : %(message)s')
ch.setFormatter(formatter)
# fh.setFormatter(formatter)
logger.addHandler(ch)
# logger.addHandler(fh)

app = Flask(__name__)
api = Api(app)
yaml = YAML()
yaml.indent(mapping=2, sequence=4, offset=2)

PATH="/controller/data.yml"
REQUESTS=None
BUF_SIZE = 65536
PREV_HASH = None
CUR_HASH = None
SLEEP_TIME = 5

if os.path.isfile(PATH):
    with open(PATH) as f:
        REQUESTS = yaml.load(f)

    sha1 = hashlib.sha1()
    with open(PATH, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            sha1.update(data)
        PREV_HASH = sha1.hexdigest()
else:
    REQUESTS = dict()
    REQUESTS["requests"] = list()


def reload_data():
    logger.debug("reload data")
    global REQUESTS
    with open(PATH) as f:
        REQUESTS = yaml.load(f)

def abort_if_request_doesnt_exist(request_id):
    search = [iii for iii in REQUESTS["requests"] if iii.get(request_id, None)]
    if len(search) < 1:
        abort(404, message="Request {} doesn't exist".format(request_id))
    return search[0][request_id]

def check_if_data_is_still_valid():
    logger.debug("check_if_data_is_still_valid")
    global PREV_HASH
    while True:
        sha1 = hashlib.sha1()
        with open(PATH, 'rb') as f:
            while True:
                data = f.read(BUF_SIZE)
                if not data:
                    break
                sha1.update(data)

        CUR_HASH = sha1.hexdigest()
        logger.debug("cur_hash: {0}, prev_hash: {1}".format(CUR_HASH, PREV_HASH))
        if CUR_HASH != PREV_HASH:
            PREV_HASH = CUR_HASH
            break
        time.sleep(SLEEP_TIME)
    reload_data()

def persist_data():
    with open(PATH, "w") as f:
        yaml.dump(REQUESTS, f)

def wait_untill_enabled(request_id):
    logger.debug("wait_untill_enabled")
    while True:
        check_if_data_is_still_valid()
        search = [iii for iii in REQUESTS["requests"] if iii.get(request_id, None)]
        logger.debug("request: {0} enabled: {1}".format(request_id,"debug: " + search[0][request_id]['enabled'].lower()))
        if search[0][request_id]['enabled'].lower() == "true":
            break


parser = reqparse.RequestParser()
parser.add_argument('from')
parser.add_argument('to')
parser.add_argument('path')
parser.add_argument('enabled')
parser.add_argument('X-Forwarded-For', location='headers')

class Request(Resource):
    def get(self, request_id):
        return abort_if_request_doesnt_exist(request_id)

    def delete(self, request_id):
        search = [iii for iii in REQUESTS["requests"] if iii.get(request_id, None)]
        if len(search) < 1:
            abort(404, message="Request {} doesn't exist".format(request_id))
        REQUESTS["requests"].remove(search[0])
        persist_data()
        return '', 204

    def put(self, request_id):
        args = parser.parse_args()
        request = {'from': args['from'], 'to': args['to'], 'path': args['path'], 'enabled': args['enabled']}
        search = [iii for iii in REQUESTS["requests"] if iii.get(request_id, None)]
        if len(search) < 1:
            data = list()
            data.append({request_id: request})
            REQUESTS['requests'] += data
        else:
            data = {request_id: request}
            REQUESTS['requests'][REQUESTS["requests"].index(search[0])] = data
        persist_data()
        return request, 201


class RequestList(Resource):
    def get(self):
        return REQUESTS["requests"]

    def post(self):
        args = parser.parse_args()
        request_id = str(uuid.uuid4())
        req_from = "Unknown"
        if args['X-Forwarded-For'] != None :
            req_from = args['X-Forwarded-For']
        elif args['from'] != None:
            req_from = args['from']
        else:
            req_from = "Unknown"
        request = {'from': req_from, 'to': args['to'], 'path': args['path'], 'enabled': args['enabled']}
        data = list()
        data.append({request_id: request})
        REQUESTS['requests'] += data
        persist_data()
        wait_untill_enabled(request_id)
        # return REQUESTS['requests'], 201
        return request, 201

api.add_resource(RequestList, '/requests')
api.add_resource(Request, '/requests/<request_id>')


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
