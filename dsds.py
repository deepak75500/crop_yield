from flask import Flask, render_template, request, jsonify
import app3
app = Flask(__name__)

@app.route('/')
def home():
    return render_template('roc.html')

@app.route('/connect', methods=['POST'])
def connect():
    data = request.json
    db_type = data.get("db_type")
    host = data.get("host", "localhost")
    user = data.get("user", "root")
    password = data.get("password", "root")
    database = data.get("database", "test")

    if db_type == "mysql":
        result = app3.connect_mysql(host, user, password, database)
    elif db_type == "mongodb":
        result = app3.connect_mongodb(host)
    else:
        result = {"status": "error", "message": "Unsupported DB type."}
    return jsonify(result)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
