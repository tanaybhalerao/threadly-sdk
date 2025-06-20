from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/ping", methods=["GET"])
def ping():
    return "✅ Flask is running!"

@app.route("/echo", methods=["POST"])
def echo():
    data = request.json
    print("📩 Data received:", data)
    return jsonify({"you_sent": data})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5050)

