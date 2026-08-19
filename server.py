from flask import Flask, request, Response, jsonify
import subprocess
import urllib.request
import os
import json
import tempfile

app = Flask(__name__)

@app.route('/', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'service': 'yt-dlp audio stream proxy',
        'note': 'POST / with {"url": "https://youtube.com/watch?v=..."}'
    })

@app.route('/', methods=['POST'])
def extract_and_stream():
    try:
        data = request.get_json(force=True)
        video_url = data.get('url')
        if not video_url:
            return jsonify({'error': 'Missing url parameter'}), 400

        # Sử dụng android_music/android client để bypass botguard hoàn toàn
        result = subprocess.run(
            [
                'yt-dlp',
                '--extractor-args', 'youtube:player_client=android_music,android,mweb',
                '-f', 'bestaudio[ext=m4a]/bestaudio/best',
                '--no-playlist',
                '-g',
                video_url
            ],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip().split('\n')[-1] if result.stderr.strip() else 'yt-dlp failed'
            print(f'[ERROR] yt-dlp failed: {error_msg}')
            return jsonify({'error': error_msg}), 500

        stream_url = result.stdout.strip().split('\n')[0]
        if not stream_url:
            return jsonify({'error': 'No stream URL returned'}), 500

        print(f'[OK] Stream URL obtained, starting proxy stream...')

        # Stream proxy: Fly.io server (cùng IP đã tạo URL) tải và pipe bytes về iOS
        def generate():
            req = urllib.request.Request(
                stream_url,
                headers={
                    'User-Agent': 'com.google.android.apps.youtube.music/6.40.52 (Linux; U; Android 11)',
                    'Referer': 'https://music.youtube.com/',
                    'Origin': 'https://music.youtube.com'
                }
            )
            with urllib.request.urlopen(req, timeout=120) as remote:
                while True:
                    chunk = remote.read(65536)  # 64KB chunks
                    if not chunk:
                        break
                    yield chunk

        return Response(
            generate(),
            mimetype='audio/mp4',
            headers={
                'Access-Control-Allow-Origin': '*',
                'Content-Disposition': 'attachment; filename="audio.m4a"',
                'X-Content-Type-Options': 'nosniff'
            }
        )

    except subprocess.TimeoutExpired:
        return jsonify({'error': 'yt-dlp timeout (30s)'}), 504
    except Exception as e:
        print(f'[ERROR] {str(e)}')
        return jsonify({'error': str(e)}), 500

@app.route('/', methods=['OPTIONS'])
def options():
    return Response(status=200, headers={
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

