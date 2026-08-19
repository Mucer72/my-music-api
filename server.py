from flask import Flask, request, Response, jsonify
import subprocess
import urllib.request
import os
import json
import tempfile
import threading

app = Flask(__name__)

@app.route('/', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'service': 'yt-dlp audio stream proxy v2',
        'note': 'POST / with {"url": "...", "cookies": "# Netscape HTTP Cookie File\\n..."}'
    })

@app.route('/', methods=['POST'])
def extract_and_stream():
    cookie_file_path = None
    try:
        data = request.get_json(force=True)
        video_url = data.get('url')
        cookie_str = data.get('cookies', '')

        if not video_url:
            return jsonify({'error': 'Missing url parameter'}), 400

        # Ghi cookies ra file tạm nếu có
        if cookie_str and len(cookie_str) > 20:
            tmp = tempfile.NamedTemporaryFile(
                mode='w', delete=False, suffix='.txt', prefix='yt_cookies_'
            )
            if not cookie_str.strip().startswith('# Netscape'):
                # Chuyển đổi "key=value; key2=value2" sang Netscape format
                lines = ['# Netscape HTTP Cookie File']
                for part in cookie_str.split(';'):
                    part = part.strip()
                    if '=' in part:
                        k, v = part.split('=', 1)
                        lines.append(f'.youtube.com\tTRUE\t/\tTRUE\t2147483647\t{k.strip()}\t{v.strip()}')
                tmp.write('\n'.join(lines))
            else:
                tmp.write(cookie_str)
            tmp.close()
            cookie_file_path = tmp.name
            print(f'[INFO] Cookie file written: {os.path.getsize(cookie_file_path)} bytes')

        # Xây dựng lệnh yt-dlp với fallback chain
        cmd = [
            'yt-dlp',
            '--extractor-args', 'youtube:player_client=android_music,android,mweb,web_embedded,tv_embedded',
            '-f', 'bestaudio[ext=m4a]/bestaudio/best',
            '--no-playlist',
            '-g',
            video_url
        ]

        if cookie_file_path:
            cmd += ['--cookies', cookie_file_path]

        print(f'[INFO] Running yt-dlp for: {video_url}')
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        # Dọn file cookie sau khi lấy URL xong
        if cookie_file_path and os.path.exists(cookie_file_path):
            try:
                os.remove(cookie_file_path)
                cookie_file_path = None
            except Exception:
                pass

        if result.returncode != 0:
            error_msg = result.stderr.strip().split('\n')[-1] if result.stderr.strip() else 'yt-dlp failed'
            print(f'[ERROR] yt-dlp failed: {error_msg}')
            return jsonify({'error': error_msg}), 500

        stream_url = result.stdout.strip().split('\n')[0]
        if not stream_url or not stream_url.startswith('http'):
            return jsonify({'error': 'Invalid stream URL returned by yt-dlp'}), 500

        print(f'[OK] Stream URL ready, proxying audio...')

        # Stream proxy: Fly.io dùng chính IP của mình để tải và pipe về iOS
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
            }
        )

    except subprocess.TimeoutExpired:
        return jsonify({'error': 'yt-dlp timeout (30s)'}), 504
    except Exception as e:
        print(f'[ERROR] {str(e)}')
        return jsonify({'error': str(e)}), 500
    finally:
        # Đảm bảo dọn file cookie dù có lỗi
        if cookie_file_path and os.path.exists(cookie_file_path):
            try:
                os.remove(cookie_file_path)
            except Exception:
                pass

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

