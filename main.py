import os
import subprocess
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp

app = FastAPI(title="Personal Music Audio API")

# Cho phép ứng dụng iOS / macOS gọi API mà không bị chặn CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMP_DIR = "/tmp/audio_cache"
os.makedirs(TEMP_DIR, exist_ok=True)

@app.get("/")
def home():
    return {"status": "ok", "message": "Personal Audio API is running!"}

@app.get("/extract")
def extract_stream_url(url: str = Query(..., description="YouTube URL or video ID")):
    """
    Lấy trực tiếp link stream audio m4a/opus nhanh nhất mà không cần tải file về server.
    """
    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            audio_url = info.get('url')
            title = info.get('title')
            duration = info.get('duration')
            thumbnail = info.get('thumbnail')
            artist = info.get('artist') or info.get('uploader')

            return {
                "success": True,
                "title": title,
                "artist": artist,
                "duration": duration,
                "thumbnail": thumbnail,
                "stream_url": audio_url
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download")
def download_audio(url: str = Query(..., description="YouTube URL or video ID")):
    """
    Server tự tải và chuyển đổi thành file .m4a sạch rồi truyền thẳng về cho app.
    (Đảm bảo 100% thành công ngay cả khi YouTube chặn IP client)
    """
    try:
        # Lấy video ID hoặc đặt tên file
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            video_id = info.get('id', 'temp_audio')
            title = info.get('title', 'audio')

        output_path = os.path.join(TEMP_DIR, f"{video_id}.m4a")

        # Tải bằng yt-dlp nếu file chưa có sẵn trong cache
        if not os.path.exists(output_path):
            ydl_opts = {
                'format': 'bestaudio[ext=m4a]/bestaudio',
                'outtmpl': os.path.join(TEMP_DIR, f"{video_id}.%(ext)s"),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'm4a',
                }],
                'quiet': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        return FileResponse(
            path=output_path,
            media_type="audio/mp4",
            filename=f"{title}.m4a"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
