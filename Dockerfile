FROM python:3.12-slim

# Cài đặt ffmpeg (cần cho yt-dlp merge audio/video)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Cài đặt Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy source code
COPY server.py /app/server.py

WORKDIR /app

# Expose port
EXPOSE 8080

# Chạy server
CMD ["python", "server.py"]

