FROM python:3.10-slim

WORKDIR /app

# Install FFmpeg and essential tools
RUN apt-get update && \
    apt-get install -y ffmpeg curl && \
    apt-get clean

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p downloads

EXPOSE 5000

# Using Gunicorn for production performance
RUN pip install gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--threads", "8", "--timeout", "0", "app.py:app"]