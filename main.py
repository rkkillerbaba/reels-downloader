import os
from urllib.parse import urlparse, unquote
from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from flask_cors import CORS
import yt_dlp
import requests

app = Flask(__name__, static_folder='static')
CORS(app)  # allow browser frontend to call API

def pick_best_format(info):
    """Pick a good direct URL from yt-dlp info dict."""
    if not info:
        return None
    # If extractor returned a direct 'url' (single-format)
    if info.get('url') and info.get('ext'):
        return {'url': info['url'], 'ext': info.get('ext'), 'format_id': info.get('format_id')}

    formats = info.get('formats') or []
    best = None
    for f in formats:
        # require a url
        if not f.get('url'):
            continue
        score = 0
        # prefer mp4
        if f.get('ext') == 'mp4':
            score += 30
        # prefer formats that include audio
        if f.get('acodec') and f.get('acodec') != 'none':
            score += 20
        # higher resolution better
        score += int(f.get('height') or 0)
        # add tbr (bitrate) influence
        score += int((f.get('tbr') or 0) / 10)
        if best is None or score > best['score']:
            best = {'format': f, 'score': score}
    if best:
        f = best['format']
        return {'url': f.get('url'), 'ext': f.get('ext'), 'format_id': f.get('format_id'), 'filesize': f.get('filesize')}
    return None

@app.route('/')
def home():
    return 'Reels & Pinterest Downloader API is live. Open /ui for the frontend.'

@app.route('/ui')
def ui():
    return send_from_directory('static', 'index.html')

@app.route('/download', methods=['GET'])
def download_info():
    """
    Returns JSON with title, thumbnail and direct video_url (not downloaded by server).
    Example:
      /download?url=https://www.instagram.com/reel/ABCDE
    """
    target_url = request.args.get('url')
    if not target_url:
        return jsonify({'error': 'Missing "url" parameter'}), 400

    try:
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'nocheckcertificate': True,
            'noplaylist': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=False)
            best = pick_best_format(info)
            if not best:
                return jsonify({'error': 'No downloadable format found', 'raw_info': info}), 500

            return jsonify({
                'title': info.get('title'),
                'thumbnail': info.get('thumbnail'),
                'uploader': info.get('uploader'),
                'video_url': best['url'],
                'ext': best.get('ext'),
                'filesize': best.get('filesize')
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/fetch', methods=['GET'])
def fetch_proxy():
    """
    Proxy endpoint that streams the remote video through this server.
    Use only when necessary (e.g., CORS/expiry issues). This will use your server bandwidth.
    Example:
      /fetch?url=<direct_video_url>
    """
    remote = request.args.get('url')
    if not remote:
        return jsonify({'error': 'Missing "url" parameter'}), 400
    try:
        # simple user-agent to avoid some blocking
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)'}
        r = requests.get(remote, stream=True, headers=headers, timeout=20)
        r.raise_for_status()

        # try to infer filename
        path = urlparse(remote).path or ''
        filename = unquote(os.path.basename(path)) or 'video'
        ctype = r.headers.get('content-type', '')
        if '.' not in filename:
            ext = ''
            if '/' in ctype:
                ext = ctype.split('/')[-1].split(';')[0]
            if ext:
                filename = f"{filename}.{ext}"

        def generate():
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk

        resp_headers = {'Content-Type': r.headers.get('content-type', 'application/octet-stream'),
                        'Content-Disposition': f'attachment; filename="{filename}"'}
        return Response(stream_with_context(generate()), headers=resp_headers)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
