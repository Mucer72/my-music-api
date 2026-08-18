from http.server import BaseHTTPRequestHandler
import json
import urllib.parse
import yt_dlp

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        video_url = params.get('url', [''])[0]

        # 1. Kiểm tra trạng thái nếu không truyền ?url=
        if not video_url:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "ok",
                "message": "My Music API is running on Vercel!"
            }).encode())
            return

        # 2. Cấu hình yt-dlp giả lập Android & iOS client để bypass 100% lỗi Botguard
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios', 'mweb']
                }
            }
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': True,
                    'title': info.get('title'),
                    'artist': info.get('artist') or info.get('uploader'),
                    'duration': info.get('duration'),
                    'stream_url': info.get('url')
                }).encode())
        except Exception as e:
            # Fallback nếu client đầu tiên gặp vấn đề
            try:
                fallback_opts = {
                    'format': 'bestaudio/best',
                    'quiet': True,
                    'no_warnings': True,
                    'skip_download': True,
                    'extractor_args': {
                        'youtube': {
                            'player_client': ['mweb', 'web_safari']
                        }
                    }
                }
                with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                    info = ydl.extract_info(video_url, download=False)
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'success': True,
                        'title': info.get('title'),
                        'artist': info.get('artist') or info.get('uploader'),
                        'duration': info.get('duration'),
                        'stream_url': info.get('url')
                    }).encode())
            except Exception as e2:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e2)}).encode())
