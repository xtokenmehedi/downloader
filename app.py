from flask import Flask, request, jsonify, render_template, send_from_directory
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
DOWNLOAD_FOLDER = 'downloads'

if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

class Logger:
    def __init__(self, tid): 
        self.tid = tid
    def debug(self, msg): 
        if self.tid in tasks: tasks[self.tid]['logs'].append(msg)
    def warning(self, msg): 
        if self.tid in tasks: tasks[self.tid]['logs'].append(f"⚠️ {msg}")
    def error(self, msg): 
        if self.tid in tasks: tasks[self.tid]['logs'].append(f"❌ {msg}")

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
    except: pass

def worker(tid, data):
    opts = {
        'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
        'logger': Logger(tid),
        'progress_hooks': [progress_hook],
        'ratelimit': int(data.get('limit', 0)) * 1024 * 1024 if data.get('limit') else None,
        'proxy': data.get('proxy'),
        
        # --- BYPASS & AUTHENTICATION ---
        'username': 'oauth2', # OAuth2 Authentication (No cookies needed)
        'extractor_args': {'youtube': {'player_client': ['ios', 'android', 'web']}},
        'geo_bypass': True,
        'nocheckcertificate': True,
    }
    
    fmt = data.get('format', 'mp4')
    if fmt == 'mp3':
        opts.update({'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '320'}]})
    
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            # Extract info with TID context
            info = ydl.extract_info(data['url'], download=True)
            filename = ydl.prepare_filename(info)
            
            # Find the actual final file (handling mergers)
            base_name = os.path.basename(filename).rsplit('.', 1)[0]
            for f in os.listdir(DOWNLOAD_FOLDER):
                if f.startswith(base_name):
                    tasks[tid]['file'] = f
                    break
        tasks[tid]['status'] = 'completed'
    except Exception as e:
        tasks[tid]['status'] = 'failed'
        if tid in tasks: tasks[tid]['logs'].append(str(e))

@app.route('/')
def home(): return render_template('index.html')

@app.route('/api/download', methods=['POST'])
def start():
    data = request.json
    tid = str(uuid.uuid4())[:8]
    tasks[tid] = {'progress': '0%', 'speed': '0B/s', 'eta': '00:00', 'logs': [], 'status': 'active', 'file': None}
    threading.Thread(target=worker, args=(tid, data)).start()
    return jsonify({'tid': tid})

@app.route('/api/status/<tid>')
def status(tid):
    if tid in tasks:
        current_logs = list(tasks[tid]['logs'])
        tasks[tid]['logs'] = []
        return jsonify({**tasks[tid], 'logs': current_logs})
    return jsonify({'error': 'Not Found'}), 404

@app.route('/api/files/<path:filename>')
def download_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
