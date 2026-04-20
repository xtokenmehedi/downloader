from flask import Flask, request, jsonify, render_template
import yt_dlp
import os
import threading
import uuid
import requests
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1

app = Flask(__name__)

# Global Task Storage
tasks = {}

class Logger:
    def __init__(self, tid): self.tid = tid
    def debug(self, msg): tasks[self.tid]['logs'].append(msg)
    def warning(self, msg): tasks[self.tid]['logs'].append(f"⚠️ {msg}")
    def error(self, msg): tasks[self.tid]['logs'].append(f"❌ {msg}")

def progress_hook(d):
    tid = d.get('info_dict', {}).get('__tid')
    if tid and tid in tasks:
        if d['status'] == 'downloading':
            tasks[tid]['progress'] = d.get('_percent_str', '0%').strip()
            tasks[tid]['speed'] = d.get('_speed_str', 'N/A')
            tasks[tid]['eta'] = d.get('_eta_str', 'N/A')
        elif d['status'] == 'finished':
            tasks[tid]['progress'] = '100%'

def fetch_metadata(filepath, title):
    try:
        res = requests.get(f"https://itunes.apple.com/search?term={title}&limit=1").json()
        if res['resultCount'] > 0:
            item = res['results'][0]
            img = requests.get(item['artworkUrl100'].replace('100x100', '600x600')).content
            audio = MP3(filepath, ID3=ID3)
            if audio.tags is None: audio.add_tags()
            audio.tags.add(TIT2(encoding=3, text=item['trackName']))
            audio.tags.add(TPE1(encoding=3, text=item['artistName']))
            audio.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=img))
            audio.save()
            return True
    except: return False

def worker(tid, data):
    opts = {
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'logger': Logger(tid),
        'progress_hooks': [progress_hook],
        'ratelimit': int(data.get('limit', 0)) * 1024 * 1024 if data.get('limit') else None,
        'proxy': data.get('proxy'),
    }
    
    fmt = data.get('format', 'mp4')
    if fmt == 'mp3':
        opts.update({'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '320'}]})
    
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(data['url'], download=False)
            info['__tid'] = tid
            ydl.download([data['url']])
            if fmt == 'mp3':
                final_path = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.mp3'
                fetch_metadata(final_path, info.get('title'))
        tasks[tid]['status'] = 'completed'
    except Exception as e:
        tasks[tid]['status'] = 'failed'
        tasks[tid]['logs'].append(str(e))

@app.route('/')
def home(): return render_template('index.html')

@app.route('/api/download', methods=['POST'])
def start():
    data = request.json
    tid = str(uuid.uuid4())[:8]
    tasks[tid] = {'progress': '0%', 'speed': '0B/s', 'eta': '00:00', 'logs': [], 'status': 'active'}
    threading.Thread(target=worker, args=(tid, data)).start()
    return jsonify({'tid': tid})

@app.route('/api/status/<tid>')
def status(tid):
    if tid in tasks:
        current_logs = list(tasks[tid]['logs'])
        tasks[tid]['logs'] = [] # Clear logs after polling
        return jsonify({**tasks[tid], 'logs': current_logs})
    return jsonify({'error': 'Not Found'}), 404

if __name__ == '__main__':
    app.run(port=5000)