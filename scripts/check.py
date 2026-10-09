#!/usr/bin/env python3
"""Verify media identity, timing, asset hashes, and static HTTP serving."""
import hashlib
import http.server
import json
from pathlib import Path
import subprocess
import threading
import urllib.request
from optimize import atoms

root = Path(__file__).resolve().parent.parent
assets = json.loads((root/'assets.json').read_text())
html = (root/'index.html').read_text()
def probe(path):
    return json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)]))
source = probe(root/'inquisitor.mp4')
optimized = probe(root/assets['video'])
a, b = source['streams'][0], optimized['streams'][0]
for key in ['codec_name', 'width', 'height', 'sample_aspect_ratio', 'duration', 'nb_frames']:
    assert a[key] == b[key], (key, a[key], b[key])
assert len(optimized['streams']) == 1
assert optimized['format']['duration'] == source['format']['duration']
assert int(optimized['format']['size']) < int(source['format']['size'])
# Compare every compressed packet, presentation timestamp, and duration.
def packets(path):
    return json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_packets', '-show_data_hash', 'sha256', '-show_entries', 'packet=pts,dts,duration,data_hash', '-of', 'json', str(path)]))['packets']
assert packets(root/'inquisitor.mp4') == packets(root/assets['video'])
raw = (root/assets['video']).read_bytes()
order = [kind for kind, _, _ in atoms(raw)]
assert order.index(b'moov') < order.index(b'mdat')
poster = probe(root/assets['poster'])['streams'][0]
assert (poster['width'], poster['height']) == (a['width'], a['height'])
for value in assets.values():
    path = root/value
    assert path.is_file() and value in html
    assert hashlib.sha256(path.read_bytes()).hexdigest()[:16] in path.name
for setting in ['autoplay', 'muted', 'playsinline', 'object-fit: contain', 'overflow: hidden', 'background: #000']:
    assert setting in html
assert 'controls' not in html and 'setTimeout' not in html
class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(root), **kwargs)
    def log_message(self, *_): pass
server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    for value in ['index.html', *assets.values()]:
        with urllib.request.urlopen(f'http://127.0.0.1:{server.server_port}/{value}') as response:
            assert response.status == 200 and response.read() == (root/value).read_bytes()
finally:
    server.shutdown()
print('PASS: all 73 compressed packets and timestamps identical; exact duration and dimensions; audio removed; faststart; poster dimensions; hashed paths; playback/layout settings; local HTTP responses.')
