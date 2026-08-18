from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp

app = FastAPI(docs_url="/docs", openapi_url="/openapi.json")

# Bật CORS để app iOS/macOS gọi được API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"status": "ok", "message": "My Music API is running on Vercel!"}

@app.get("/extract")
def extract_audio(url: str = Query(..., description="YouTube URL or video ID")):
    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "success": True,
                "title": info.get('title'),
                "artist": info.get('artist') or info.get('uploader'),
                "duration": info.get('duration'),
                "stream_url": info.get('url')
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
