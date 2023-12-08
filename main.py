from flask import Flask
from flask import request, abort, redirect
from hashlib import sha256
from redis import Redis
from secrets import token_hex


db_host = "178.62.216.119"
db_port = 4567

app = Flask(__name__)
database = Redis(host="178.62.216.119", port=4567, decode_responses = True)

if not database.ping():
    raise Exception("No access")


def authorize() ->str:
    session_id = request.args.get("session_id")
    login = database.get(f"session:{session_id}")
    if not login:
        abort(401)
    return login


@app.route("/signup")
def signup():
    login = request.args.get("login")
    password1 = request.args.get("password1")
    password2 = request.args.get("password2")

    if None in (login, password1,password2):
        abort(400)

    if password1 != password2:
        abort(403)

    hashed_password = sha256(bytes(password1.encode("UTF-8"))).hexdigest()

    existing_entry = database.get(f"user:{login}")
    if existing_entry is not None:
        abort(400)

    success = database.set(f"user:{login}", hashed_password)
    if not success:
        abort(500)

    
    return "True"

@app.route("/login")
def login():
    login = request.args.get("login")
    password = request.args.get("password")

    if None in (login,password):
        abort(400)

    expected_hash = database.get(f"user:{login}")

    if expected_hash is None:
        abort(400)

    actual_hash = sha256(password.encode("UTF-8")).hexdigest()

    if expected_hash.decode("UTF-8") != actual_hash:
        abort(400)
        
    session_id = token_hex(8)

    success = database.set(f"session:{session_id}", login, ex = 24*60*60)
    
    if not success:
        abort(500)

    return session_id

@app.route("/contacts")
def get_contacts():
    login = authorize()


    contacts = database.smembers(f"friends:{login}")
    return list(contacts)

@app.route("/add_contact")
def new_contact():
    login = authorize()
    contact = request.args.get("login")
    res = database.get(f"user:{contact}")
    if res is None():
        abort(402)
    database.sadd("friends:{login}", contact)
    database.sadd("friends:{contact}", login)

    return "True"

@app.route("/search")
def search_contacts():
    authorize()
    login = request.args.get("login")
    keys = database.keys(f"user:{login}*")
    result = []
    for key in keys:
        _, login = key.split(":")
        result.append(login)


    return result



@app.route("/delete_contact")
def delete_contact():
    login = authorize()
    contact = request.args.get("login")
    database.srem(f"friends:{login}", contact)
    database.srem(f"friends:{contact}", login)
    return "True"
    

@app.route("/broadcast_url")
def get_broadcast_url():
    session_id = request.args.get("session_id")
    if session_id is None:
        abort(400)
    login = database.get(f"session:{session_id}")
    if login is None:
        abort(400)
    return {
        "host" :  db_host,
        "port" : db_port,
        "channel_name": "broadcast"
    }

app.run("0.0.0.0", 8083)
