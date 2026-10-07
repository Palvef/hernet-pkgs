#!/usr/bin/env python3
"""Exercise installed module packages: RTMP -> HLS -> decoded audio/video; RTSP TCP."""
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import urllib.request


def port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def get(url):
    return urllib.request.urlopen(url, timeout=5).read().decode()


pv = os.environ['pv']
revision = os.environ.get('RTMP_BUILD_REVISION', '1')
module = f'/usr/lib/nginx/ha-modules/{pv}/hernet-rtmp-1.0.3-r{revision}/ngx_rtmp_module.so'
assert Path(module).is_file()
flags = subprocess.check_output(['nginx', '-V'], stderr=subprocess.STDOUT).decode()
assert 'nginx/1.31.6' in flags and '--with-stream ' in flags
for deb in Path('/out').glob('*.deb'):
    listing = subprocess.check_output(['dpkg-deb', '-c', str(deb)], text=True)
    assert './etc/nginx' not in listing and 'nginx-iptv-config' not in listing, listing
    control = subprocess.check_output(['dpkg-deb', '--ctrl-tarfile', str(deb)])
    import io, tarfile
    with tarfile.open(fileobj=io.BytesIO(control)) as archive:
        assert not any(Path(p.name).name in ['postinst', 'preinst', 'prerm', 'postrm'] for p in archive)

with tempfile.TemporaryDirectory(prefix='hernet-rtmp-') as directory:
    base = Path(directory)
    base.chmod(0o755)
    etc = base / 'etc'
    shutil.copytree('/repo/config/iptv', etc)
    shutil.copy2('/etc/nginx/mime.types', etc / 'mime.types')
    hls = base / 'hls'
    hls.mkdir(mode=0o777)
    hls.chmod(0o777)
    web = base / 'web'
    web.mkdir()
    (web / 'index.html').write_text('HerNet IPTV test')
    http_port, rtmp_port, rtsp_port, backend_port = [port() for _ in range(4)]
    for path in etc.rglob('*'):
        if path.is_file():
            s = path.read_text().replace('@RTMP_MODULE@', module).replace('/etc/nginx', str(etc))
            s = s.replace('/tmp/hls', str(hls)).replace('/usr/local/nginx/html/iptv', str(web))
            s = s.replace('/run/nginx.pid', str(base / 'nginx.pid'))
            s = s.replace('/var/log/nginx/error.log', str(base / 'error.log'))
            s = s.replace('/var/log/nginx/access.log', str(base / 'access.log'))
            s = s.replace('listen 80;', f'listen 127.0.0.1:{http_port};').replace('listen [::]:80;', '')
            s = s.replace('listen 1935;', f'listen 127.0.0.1:{rtmp_port};')
            path.write_text(s)
    (etc / 'stream-conf.d/rtsp.conf').write_text(
        f'server {{ listen 127.0.0.1:{rtsp_port}; proxy_pass 127.0.0.1:{backend_port}; }}\n')
    backend = socket.socket()
    backend.bind(('127.0.0.1', backend_port))
    backend.listen(1)

    def rtsp_backend():
        conn, _ = backend.accept()
        with conn:
            request = conn.recv(4096)
            assert request.startswith(b'OPTIONS '), request
            conn.sendall(b'RTSP/1.0 200 OK\r\nCSeq: 1\r\nPublic: OPTIONS, DESCRIBE, SETUP, PLAY\r\n\r\n')

    worker = threading.Thread(target=rtsp_backend, daemon=True)
    worker.start()
    command = ['nginx', '-p', str(base) + '/', '-c', str(etc / 'nginx.conf')]
    subprocess.run(command + ['-t'], check=True)
    subprocess.run(command, check=True)
    publisher = None
    try:
        with socket.create_connection(('127.0.0.1', rtsp_port), timeout=5) as client:
            client.sendall(b'OPTIONS rtsp://127.0.0.1/test RTSP/1.0\r\nCSeq: 1\r\n\r\n')
            response = client.recv(4096)
            assert response.startswith(b'RTSP/1.0 200 OK'), response
        print('PASS official built-in stream forwards real RTSP OPTIONS request/response')
        publisher = subprocess.Popen([
            'ffmpeg', '-v', 'error', '-re', '-f', 'lavfi', '-i', 'testsrc=size=320x240:rate=25',
            '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=44100', '-t', '40',
            '-c:v', 'libx264', '-threads', '1', '-preset', 'ultrafast', '-tune', 'zerolatency',
            '-pix_fmt', 'yuv420p', '-g', '75', '-sc_threshold', '0', '-c:a', 'aac',
            '-f', 'flv', f'rtmp://127.0.0.1:{rtmp_port}/live/probe'],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        url = f'http://127.0.0.1:{http_port}/hls/probe.m3u8'
        deadline = time.monotonic() + 25
        initial = None
        while time.monotonic() < deadline:
            if publisher.poll() is not None:
                raise RuntimeError(publisher.stderr.read().decode())
            try:
                playlist = get(url)
                if '#EXTINF:' in playlist:
                    initial = playlist
                    break
            except Exception:
                pass
            time.sleep(1)
        assert initial, 'No HLS playlist after RTMP publish'
        durations = [float(line.split(':', 1)[1].strip(',')) for line in initial.splitlines() if line.startswith('#EXTINF:')]
        assert all(2.5 <= d <= 3.5 for d in durations), durations
        time.sleep(4)
        assert get(url) != initial, 'HLS playlist did not advance'
        probe = json.loads(subprocess.check_output([
            'ffprobe', '-v', 'error', '-show_entries', 'stream=codec_name,width,height', '-of', 'json', url], timeout=15))
        assert any(s.get('width') == 320 and s.get('height') == 240 for s in probe['streams']), probe
        assert any(s['codec_name'] == 'aac' for s in probe['streams']), probe
        decoded = subprocess.run([
            'ffmpeg', '-v', 'error', '-xerror', '-i', url,
            '-map', '0:v:0', '-map', '0:a:0', '-t', '1',
            '-progress', 'pipe:1', '-f', 'null', '-'],
            check=True, timeout=15, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        frames = [int(v) for v in re.findall(r'^frame=(\d+)$', decoded.stdout, re.M)]
        assert frames and max(frames) > 0, decoded
        print('PASS installed RTMP module publishes live/probe, HTTP HLS advances with 3s fragments, video/audio decode')
        print(json.dumps(probe, sort_keys=True))
        print('Decoded frames:', max(frames))
    finally:
        if publisher is not None and publisher.poll() is None:
            publisher.terminate()
            publisher.communicate(timeout=10)
        subprocess.run(command + ['-s', 'quit'], check=True)
        backend.close()
