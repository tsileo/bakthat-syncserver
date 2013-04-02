# -*- encoding: utf-8 -*-
from flask import Flask, jsonify, request, Response
from flask.views import MethodView
from datetime import datetime
from bson import ObjectId
from pymongo import Connection
import json
from functools import wraps
from slugify import slugify

LOGIN = "login"
PASSWORD = "password"

con = Connection()
db = con["bakthatsyncserver"]
backups_col = db["backups"]
clients_col = db["clients"]


class MongoDocumentEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        elif isinstance(o, ObjectId):
            return str(o)
        return json.JSONEncoder(self, o)


def mongodoc_jsonify(*args, **kwargs):
    return Response(json.dumps(dict(*args, **kwargs), cls=MongoDocumentEncoder), mimetype='application/json')


def check_auth(username, password):
    return username == LOGIN and password == PASSWORD


def authenticate(message="Authenticate."):
    message = {'message': message}
    resp = jsonify(message)

    resp.status_code = 401
    resp.headers['WWW-Authenticate'] = 'Basic realm="Example"'

    return resp


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth:
            return authenticate()
        elif not check_auth(auth.username, auth.password):
            return authenticate("Authentication Failed.")

        if not request.headers.get("bakthat-client"):
            resp = jsonify(message="Missing header.")
            resp.status_code = 400
            return resp

        return f(*args, **kwargs)

    return decorated


app = Flask(__name__)
app.debug = True


@requires_auth
@app.route("/backups/sync", methods=['POST'])
def backups_sync():
    print request.json
    sync_result = {}

    last_sync_ts = request.json.get("sync_ts")
    to_insert_in_bakthat = []
    for mongo_backup in backups_col.find({"meta.user": request.authorization.username,
                                          "meta.sync": {"$gt": last_sync_ts}}):
        del mongo_backup["_id"]
        del mongo_backup["meta"]
        mongo_backup["tags"] = u" ".join(mongo_backup["tags"])
        to_insert_in_bakthat.append(mongo_backup)

    to_insert_in_mongo = request.json.get("new")
    sync_ts = int(datetime.utcnow().strftime("%s"))
    for backup in to_insert_in_mongo:
        mongo_backup = backups_col.find_one({"stored_filename": "stored_filename"})
        backup["tags"] = backup["tags"].split()
        meta = dict(user=request.authorization.username,
                    sync=sync_ts)
        backup["meta"] = meta
        backups_col.update({"stored_filename": backup["stored_filename"],
                            "meta.user": request.authorization.username},
                           {"$set": backup}, upsert=True)

    sync_result["updated"] = to_insert_in_bakthat
    sync_result["sync_ts"] = sync_ts
    print sync_result
    return mongodoc_jsonify(**sync_result)


class BackupsAPI(MethodView):
    decorators = [requires_auth]

    def get(self, backup_id):
        if backup_id is None:
            return mongodoc_jsonify(backups=list(backups_col.find({"user": request.authorization.username})))
        else:
            return mongodoc_jsonify(**backups_col.find_one({"user": request.authorization.username, "stored_filename": backup_id}))

    def post(self):
        #{'stored_filename': 'tmpkPrHG7.20130227175351.tgz', 'size': 152, 'metadata': {'is_enc': False}, 'backup_date': datetime.datetime(2013, 2, 27, 17, 53, 51, 612680), 'filename': 'tmpkPrHG7'}
        backup = request.json.copy()
        backup["user"] = request.authorization.username
        if not backups_col.find_one({"stored_filename": backup["stored_filename"]}):
            backups_col.insert(backup)
            return mongodoc_jsonify(**backup)
        else:
            return mongodoc_jsonify()

#    def delete(self, backup_id):
#        # delete a single user
#        backups_col.remove({"stored_filename": backup_id, "user": request.authorization.username})
#        return jsonify()

#    def put(self, backup_id):
#        # update a single user
#        pass

backups_view = BackupsAPI.as_view('backups_api')
app.add_url_rule('/backups', defaults={'backup_id': None},
                 view_func=backups_view, methods=['GET'])
app.add_url_rule('/backups', view_func=backups_view, methods=['POST'])
app.add_url_rule('/backups/<backup_id>', view_func=backups_view,
                 methods=['GET', 'PUT', 'DELETE'])


class ClientsAPI(MethodView):
    decorators = [requires_auth]

    def get(self, client_id):
        if client_id is None:
            return mongodoc_jsonify(backups=list(clients_col.find({"user": request.authorization.username})))
        else:
            return mongodoc_jsonify(**clients_col.find_one({"user": request.authorization.username, "_id": client_id}))

    def post(self):
        #client = request.json.copy()
        client = {}
        client["client"] = request.headers.get("bakthat-client")
        client["slug"] = slugify(client["client"].decode())
        client["user"] = request.authorization.username
        client["last_sync"] = None
        existing_client = clients_col.find_one({"client": client["client"], "user": client["user"]})
        if not existing_client:
            clients_col.insert(client)
            return mongodoc_jsonify(**client)
        else:
            return mongodoc_jsonify(**existing_client)

#    def delete(self, backup_id):
#        # delete a single user
#        backups_col.remove({"stored_filename": backup_id, "user": request.authorization.username})
#        return jsonify()

#    def put(self, backup_id):
#        # update a single user
#        pass

clients_view = ClientsAPI.as_view('clients_api')
app.add_url_rule('/clients', defaults={'client_id': None},
                 view_func=clients_view, methods=['GET'])
app.add_url_rule('/clients', view_func=clients_view, methods=['POST'])
app.add_url_rule('/clients/<client_id>', view_func=clients_view,
                 methods=['GET', 'PUT', 'DELETE'])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=2405)
