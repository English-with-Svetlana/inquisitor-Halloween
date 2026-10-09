#!/usr/bin/env python3
"""Compress this edit-list-based MP4 without changing its presentation timing and update hashed references."""
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
    """Restore the original edit window and irregular final sample duration.

    Rebuild the timing atom tree and shift chunk offsets if moov grows.
    Encoding all frames with the edit list disabled preserves the hidden
    preroll frames as well as the displayed animation.
    """
    src, dst = source.read_bytes(), target.read_bytes()
    sm, dm = child(src, (0, len(src)), b'moov'), child(dst, (0, len(dst)), b'moov')
    st, dt = video_track(src, sm), video_track(dst, dm)
    if sum(k == b'trak' for k, _, _ in atoms(dst, *dm)) != 1:
        raise ValueError('Expected one silent video track')
    replacements = {}
    for kind, ps, pd in [(b'mvhd', sm, dm), (b'tkhd', st, dt)]:
        sa, sb = child(src, ps, kind)
        da, db = child(dst, pd, kind)
        if src[sa] != 0 or dst[da] != 0:
            raise ValueError('Only version-0 timing is supported')
        payload = bytearray(dst[da:db])
        offset, count = (12, 8) if kind == b'mvhd' else (20, 4)
        payload[offset:offset+count] = src[sa+offset:sa+offset+count]
        replacements[kind] = bytes(payload)
    for kind, ps, pd in [
        (b'elst', child(src, st, b'edts'), child(dst, dt, b'edts')),
        (b'mdhd', child(src, st, b'mdia'), child(dst, dt, b'mdia')),
        (b'stts', child(src, child(src, child(src, st, b'mdia'), b'minf'), b'stbl'),
         child(dst, child(dst, child(dst, dt, b'mdia'), b'minf'), b'stbl'))]:
        sa, sb = child(src, ps, kind)
        replacements[kind] = src[sa:sb]
    containers = {b'moov', b'trak', b'edts', b'mdia', b'minf', b'stbl'}
    def rebuild(data, span, shift):
        result = bytearray()
        for kind, a, b in atoms(data, *span):
            payload = data[a:b]
            if kind in containers:
                payload = rebuild(data, (a, b), shift)
            elif kind in replacements:
                payload = replacements[kind]
            elif kind in (b'stco', b'co64'):
                payload = bytearray(payload)
                count = struct.unpack_from('>I', payload, 4)[0]
                width, fmt = (4, '>I') if kind == b'stco' else (8, '>Q')
                for i in range(count):
                    position = 8 + i * width
                    value = struct.unpack_from(fmt, payload, position)[0]
                    struct.pack_into(fmt, payload, position, value + shift)
            result.extend(struct.pack('>I4s', len(payload)+8, kind)+payload)
        return bytes(result)
    original_size = dm[1]-dm[0]
    shift = len(rebuild(dst, dm, 0))-original_size
    moov = rebuild(dst, dm, shift)
    # Encoder output is ordinary faststart MP4 with an 8-byte moov header.
    target.write_bytes(dst[:dm[0]-8] + struct.pack('>I4s', len(moov)+8, b'moov')
                       + moov + dst[dm[1]:])


def validate_timing(source, target):
    def probe(path):
        return json.loads(run('ffprobe', '-v', 'error', '-show_streams',
                              '-show_format', '-of', 'json', str(path)))
    original, compressed = probe(source), probe(target)
    a, b = original['streams'][0], compressed['streams'][0]
    for key in ['width', 'height', 'sample_aspect_ratio', 'duration', 'nb_frames']:
        if a[key] != b[key]:
            raise ValueError(f'Compression changed {key}')
    if len(compressed['streams']) != 1 or b['codec_type'] != 'video':
        raise ValueError('Playback file must contain only video')
    if original['format']['duration'] != compressed['format']['duration']:
        raise ValueError('Presentation duration changed')
    for ignore in [False, True]:
        def frames(path):
            command = ['ffprobe', '-v', 'error']
            if ignore:
                command += ['-ignore_editlist', '1']
            command += ['-select_streams', 'v:0', '-show_frames', '-show_entries',
                        'frame=pts,duration', '-of', 'json', str(path)]
            data = json.loads(run(*command))['frames']
            return [{key: frame[key] for key in ['pts', 'duration']} for frame in data]
        if frames(source) != frames(target):
            raise ValueError('Frame presentation timing changed')


def publish(path, prefix, extension):
    data = path.read_bytes()
    name = f'assets/{prefix}.{hashlib.sha256(data).hexdigest()[:16]}.{extension}'
    (ROOT / name).write_bytes(data)
    return name

def main():
    source = ROOT / 'inquisitor.mp4'
    with tempfile.TemporaryDirectory() as temp:
        video, poster = Path(temp)/'video.mp4', Path(temp)/'poster.jpg'
        run('ffmpeg', '-hide_banner', '-loglevel', 'error', '-ignore_editlist', '1', '-i', str(source),
            '-map', '0:v:0', '-an', '-vf', 'setpts=PTS-STARTPTS',
            '-c:v', 'libx264', '-preset', 'slow', '-crf', '24', '-pix_fmt', 'yuv420p',
            '-bf', '3', '-x264-params', 'b-adapt=0', '-g', '48', '-keyint_min', '48',
            '-sc_threshold', '0', '-fps_mode', 'passthrough', '-enc_time_base', '1:12288',
            '-video_track_timescale', '12288', '-movflags', '+faststart', str(video))
        restore_timing(source, video)
        validate_timing(source, video)
        # Full-resolution high-quality JPEG keeps the first-frame composition.
        run('ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', str(source),
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
