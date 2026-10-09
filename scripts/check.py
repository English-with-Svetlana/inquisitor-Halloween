#!/usr/bin/env python3
"""Verify media presentation timing, quality, asset hashes, and static HTTP serving."""
from html.parser import HTMLParser
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
assert all(stream['codec_type'] != 'audio' for stream in optimized['streams'])
assert optimized['format']['duration'] == source['format']['duration']
assert int(optimized['format']['size']) < int(source['format']['size'])
# Compression changes packet hashes, so compare decoded frame presentation
# order/timing with and without the source edit list instead.
def frames(path, ignore=False):
    command = ['ffprobe', '-v', 'error']
    if ignore:
        command += ['-ignore_editlist', '1']
    command += ['-select_streams', 'v:0', '-show_frames', '-show_entries',
                'frame=pts,duration', '-of', 'json', str(path)]
    data = json.loads(subprocess.check_output(command))['frames']
    return [{key: frame[key] for key in ['pts', 'duration']} for frame in data]
for ignore in [False, True]:
    assert frames(root/'inquisitor.mp4', ignore) == frames(root/assets['video'], ignore)
assert len(frames(root/assets['video'], True)) == 73
subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-xerror',
                '-i', str(root/assets['video']), '-an', '-f', 'null', '-'], check=True)
# SSIM compares corresponding decoded frames in order. This is a numerical
# quality check, not a substitute for watching the animation.
quality = subprocess.run(['ffmpeg', '-hide_banner', '-ignore_editlist', '1',
    '-i', str(root/'inquisitor.mp4'), '-ignore_editlist', '1',
    '-i', str(root/assets['video']), '-lavfi', '[0:v]setpts=PTS-STARTPTS[a];[1:v]setpts=PTS-STARTPTS[b];[a][b]ssim',
    '-an', '-f', 'null', '-'], capture_output=True, text=True, check=True)
import re
ssim = float(re.search(r'All:([0-9.]+)', quality.stderr).group(1))
assert ssim >= 0.96, ssim
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
class VideoAttributes(HTMLParser):
    def handle_starttag(self, tag, attrs):
        if tag == 'video':
            self.attributes = dict(attrs)
parser = VideoAttributes()
parser.feed(html)
assert 'controls' not in parser.attributes
for key in ['autoplay', 'muted', 'loop', 'playsinline']:
    assert key in parser.attributes
assert parser.attributes['preload'] == 'auto'
assert parser.attributes['src'] == assets['video']
assert parser.attributes['poster'] == assets['poster']
assert 'video.controls = false' in html and 'setTimeout' not in html
assert 'pointer-events: none' in html
assert 'aspect-ratio: 16 / 9' in html and 'place-items: center' in html
# Numeric check of the CSS width=min(viewport width, viewport height*16/9).
# This verifies the fit rule, not actual browser rendering.
for width, height in [(1920, 1080), (1280, 720), (800, 600), (390, 844), (844, 390)]:
    stage_width = min(width, height*16/9)
    stage_height = stage_width*9/16
    assert stage_width <= width and stage_height <= height + 0.0001
    assert abs(stage_width/stage_height - 16/9) < 0.0001
assert 'opacity:' not in html and 'requestVideoFrameCallback' not in html
assert 'video.loop = true' in html and 'video.volume = 0' in html
template = (root/'scripts/index.template.html').read_text()
for key, value in assets.items():
    template = template.replace('{{'+key+'}}', value)
assert html == template
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
print(f'PASS: all 73 frame timestamps/durations preserved; edited presentation preserved; SSIM {ssim:.6f}; error-free decode; exact duration/dimensions; no audio; faststart; hashed paths; native poster; looping/layout settings; local HTTP.')
