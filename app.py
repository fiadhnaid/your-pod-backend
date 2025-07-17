from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route("/")
def hello_world():
    return jsonify(message="🚀 Hello, Hackathon world!")
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))  # default 5000, override with env var
    app.run(host="0.0.0.0", port=port, debug=True)
