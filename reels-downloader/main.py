from flask import Flask, request, jsonify, send_from_directory
import instaloader
import os

app = Flask(__name__)

# Instagram download endpoint
@app.route("/download", methods=["GET"])
def download_instagram():
    try:
        url = request.args.get("url")

        if not url:
            return jsonify({"error": "URL is required"}), 400

        # Instagram logic
        loader = instaloader.Instaloader()
        loader.download_url(url, target="downloads")

        return jsonify({"message": "Download started successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Serve static files (index.html)
@app.route("/")
def home():
    return send_from_directory("static", "index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)