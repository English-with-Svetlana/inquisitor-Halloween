#!/usr/bin/env python3
"""Losslessly prepare this edit-list-based MP4 and update hashed references."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent

def run(*args):
    return subprocess.check_output(args)

def atoms(data, start=0, end=None):
    end = len(data) if end is None else end
    while start + 8 <= end:
        size, kind = struct.unpack_from('>I4s', data, start)
        header = 8
        if size == 1:
            size = struct.unpack_from('>Q', data, start + 8)[0]
            header = 16
        if size == 0:
            size = end - start
        if size < header or start + size > end:
            raise ValueError('Invalid MP4 atom')
        yield kind, start + header, start + size
        start += size

def child(data, span, kind):
    return next((a, b) for k, a, b in atoms(data, *span) if k == kind)

def video_track(data, moov):
    for kind, a, b in atoms(data, *moov):
        if kind == b'trak':
            mdia = child(data, (a, b), b'mdia')
            hdlr = child(data, mdia, b'hdlr')
            if data[hdlr[0]+8:hdlr[0]+12] == b'vide':
                return a, b
    raise ValueError('No video track')

def restore_timing(source, target):
    # FFmpeg otherwise rounds/rebuilds this source's edit list. Restore the
    # original movie time scale, track duration, and exact presentation window.
    src, dst = source.read_bytes(), bytearray(target.read_bytes())
    sm, dm = child(src, (0, len(src)), b'moov'), child(dst, (0, len(dst)), b'moov')
    st, dt = video_track(src, sm), video_track(dst, dm)
    for kind, parent_s, parent_d, offset, length in [
        (b'mvhd', sm, dm, 12, 8), (b'tkhd', st, dt, 20, 4)]:
        sa, _ = child(src, parent_s, kind)
        da, _ = child(dst, parent_d, kind)
        if src[sa] != 0 or dst[da] != 0:
            raise ValueError('Version 1 timing requires a workflow update')
        dst[da+offset:da+offset+length] = src[sa+offset:sa+offset+length]
    se = child(src, child(src, st, b'edts'), b'elst')
    de = child(dst, child(dst, dt, b'edts'), b'elst')
    if se[1]-se[0] != de[1]-de[0]:
        raise ValueError('Edit-list structure changed')
    dst[de[0]:de[1]] = src[se[0]:se[1]]
    target.write_bytes(dst)

def publish(path, prefix, extension):
    data = path.read_bytes()
    name = f'assets/{prefix}.{hashlib.sha256(data).hexdigest()[:16]}.{extension}'
    (ROOT / name).write_bytes(data)
    return name

def main():
    source = ROOT / 'inquisitor.mp4'
    with tempfile.TemporaryDirectory() as temp:
        video, poster = Path(temp)/'video.mp4', Path(temp)/'poster.jpg'
        run('ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', str(source),
            '-map', '0:v:0', '-an', '-c:v', 'copy', '-movflags', '+faststart', str(video))
        restore_timing(source, video)
        # Full-resolution high-quality JPEG keeps the first-frame composition.
        run('ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', str(video),
            '-frames:v', '1', '-c:v', 'mjpeg', '-q:v', '2', str(poster))
        assets = {'video': publish(video, 'transition', 'mp4'),
                  'poster': publish(poster, 'poster', 'jpg')}
        template = (ROOT/'scripts/index.template.html').read_text()
        for key, value in assets.items():
            template = template.replace('{{'+key+'}}', value)
        (ROOT/'index.html').write_text(template)
        (ROOT/'assets.json').write_text(json.dumps(assets, indent=2)+'\n')
        print(json.dumps({'original_bytes': source.stat().st_size,
                         'optimized_bytes': video.stat().st_size,
                         'poster_bytes': poster.stat().st_size, **assets}, indent=2))

if __name__ == '__main__':
    main()
