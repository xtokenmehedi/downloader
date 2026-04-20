FROM python:3.10-slim

WORKDIR /app

# Install FFmpeg, curl, and Node.js (Crucial for yt-dlp YouTube bypass)
RUN apt-get update && \
    apt-get install -y ffmpeg curl nodejs && \
    apt-get clean

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p downloads

EXPOSE 5000

RUN pip install gunicorn
CMD gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 2 --timeout 120 app:app
