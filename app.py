from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/")
def hello_world():
    return jsonify(message="🚀 Hello, Hackathon world!")

if __name__ == "__main__":
    # Flask’s built‑in server is fine for a POC
    app.run(host="0.0.0.0", port=5000, debug=True)
