from http.server import BaseHTTPRequestHandler
import json
import tempfile
import os
import urllib.request
import yt_dlp

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        try:
            data = json.loads(body.decode('utf-8'))
            target_url = data.get('url')
            cookie_str = data.get('cookies') or os.environ.get("YOUTUBE_COOKIES", "")
            download_mode = data.get('download', True)
            
            if not target_url:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Thiếu tham số url'}).encode('utf-8'))
                return

            cookie_file = None
            if cookie_str:
                tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt")
                if not cookie_str.startswith("# Netscape"):
                    lines = ["# Netscape HTTP Cookie File"]
                    for part in cookie_str.split(";"):
                        if "=" in part:
                            k, v = part.strip().split("=", 1)
                            lines.append(f".youtube.com\tTRUE\t/\tTRUE\t2147483647\t{k}\t{v}")
                    tmp.write("\n".join(lines))
                else:
                    tmp.write(cookie_str)
                tmp.close()
                cookie_file = tmp.name

            # CẤU HÌNH MẤU CHỐT: Dùng player_client android_music và android để bypass 100% Botguard trên cloud
            ydl_opts = {
                'format': 'bestaudio[ext=m4a]/bestaudio/best',
                'quiet': True,
                'no_warnings': True,
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android_music', 'android', 'mweb']
                    }
                }
            }
            if cookie_file:
                ydl_opts['cookiefile'] = cookie_file

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(target_url, download=False)
                stream_url = info.get('url')
                title = info.get('title')
                duration = info.get('duration')
                ext = info.get('ext', 'm4a')

            # Dọn dẹp file cookie tạm
            if cookie_file and os.path.exists(cookie_file):
                try:
                    os.remove(cookie_file)
                except Exception:
                    pass

            if not stream_url:
                raise Exception("Không tìm thấy stream URL từ yt-dlp")

            # Stream Proxy: Vercel đọc trực tiếp từ Google Video và pipe luồng nhạc về App
            if download_mode:
                req = urllib.request.Request(
                    stream_url,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36',
                        'Referer': 'https://music.youtube.com/'
                    }
                )
                with urllib.request.urlopen(req, timeout=30) as remote_stream:
                    content_length_remote = remote_stream.headers.get('Content-Length')
                    content_type_remote = remote_stream.headers.get('Content-Type', 'audio/mp4')

                    self.send_response(200)
                    self.send_header('Content-Type', content_type_remote)
                    if content_length_remote:
                        self.send_header('Content-Length', content_length_remote)
                    self.send_header('Content-Disposition', f'attachment; filename="audio.{ext}"')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()

                    while True:
                        chunk = remote_stream.read(64 * 1024)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                return

            # Chế độ trả JSON metadata
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'status': 'ok',
                'stream_url': stream_url,
                'title': title,
                'duration': duration
            }).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({
            'status': 'ok',
            'message': 'My Music API is running with Android Music client and direct audio stream proxy support!'
        }).encode('utf-8'))
