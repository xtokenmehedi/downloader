FROM python:3.10-slim

WORKDIR /app

# Install FFmpeg and curl
RUN apt-get update && \
    apt-get install -y ffmpeg curl && \
    apt-get clean

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p downloads

# Using dynamic $PORT provided by Railway
# Reduced workers and threads to prevent Out Of Memory (OOM) crash on Free Tier
RUN pip install gunicorn
CMD gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 2 --timeout 120 app:app