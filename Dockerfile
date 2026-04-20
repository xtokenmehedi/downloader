FROM python:3.10-slim

WORKDIR /app

# Install dependencies + Node.js (Required for YouTube)
RUN apt-get update && \
    apt-get install -y ffmpeg curl nodejs && \
    apt-get clean

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p downloads

# Run using Gunicorn with Railway's Dynamic Port
RUN pip install gunicorn
CMD gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 2 --timeout 0 app:app
