from http.server import BaseHTTPRequestHandler
import json
import tempfile
import os
import yt_dlp

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        # Hỗ trợ CORS preflight
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
            # Nhận cookies động từ thiết bị gửi lên, fallback sang env var nếu có
            cookie_str = data.get('cookies') or os.environ.get("YOUTUBE_COOKIES", "")
            
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
                    # Nếu client gửi chuỗi header 'k1=v1; k2=v2', chuyển sang format Netscape
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

            ydl_opts = {
                'format': 'bestaudio[ext=m4a]/bestaudio/best',
                'quiet': True,
                'no_warnings': True,
            }
            if cookie_file:
                ydl_opts['cookiefile'] = cookie_file

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(target_url, download=False)
                stream_url = info.get('url')
                title = info.get('title')
                duration = info.get('duration')

            # Xoá file cookie tạm ngay sau khi dùng xong để bảo mật
            if cookie_file and os.path.exists(cookie_file):
                try:
                    os.remove(cookie_file)
                except Exception:
                    pass

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
        # Endpoint kiểm tra trạng thái
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({
            'status': 'ok',
            'message': 'My Music API is running with dynamic cookie support!'
        }).encode('utf-8'))
