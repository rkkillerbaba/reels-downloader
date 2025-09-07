from flask import Flask, render_template, request, jsonify
import requests
import re

app = Flask(__name__, static_folder="static", static_url_path="", template_folder="static")

@app.route('/')
def home():
    return app.send_static_file('index.html')

@app.route('/download/instagram', methods=['GET'])
def instagram_download():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "Instagram URL required"}), 400
    
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        video_url = re.search(r'"video_url":"(.*?)"', response.text)
        if video_url:
            return jsonify({"download_url": video_url.group(1).replace("\\u0026", "&")})
        else:
            return jsonify({"error": "Video not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

