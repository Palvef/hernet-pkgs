#!/usr/bin/env python3
"""Real TCP preread/queue test against the patched module and example JS."""
import os
from pathlib import Path
import signal
import socket
import socketserver
import subprocess
import tempfile
import threading
import time

version=os.environ.get('NGINX_VERSION','1.31.6')
module=Path(os.environ.get('HA_MODULE_DIR','/work/nginx-'+version+'/objs'))/'ngx_stream_js_module.so'
assert Path('/work/MODULES_READY').exists(), 'Run only after successful module linking'
root=Path(tempfile.mkdtemp(prefix='ha-rsync-test-'))
class Backend(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(15)
        self.request.sendall(b'@RSYNCD: 31.0\n')
        f=self.request.makefile('rb')
        assert f.readline().startswith(b'@RSYNCD:')
        assert f.readline().strip()==b'ubuntu'
        self.request.sendall(b'@RSYNCD: OK\n')
        try:
            while self.request.recv(1024): pass
        except OSError: pass

class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address=True
    daemon_threads=True
backend=Server(('127.0.0.1',0),Backend)
threading.Thread(target=backend.serve_forever,daemon=True).start()
example=Path('/work/sources/njs/nginx/examples/rsync/rsync.conf').read_text()
example=example.replace('/etc/nginx/njs/rsync.njs','/work/sources/njs/nginx/examples/rsync/rsync.njs')
example=example.replace('listen 873;','listen 127.0.0.1:18873;').replace('listen [::]:873;','')
example=example.replace('/var/log/nginx/rsync.log',str(root/'access.log'))
example=example.replace("'120'", "'3'").replace(' 60;', ' 1;')
example=example.replace('192.0.2.10:873','127.0.0.1:'+str(backend.server_address[1])).replace('192.0.2.20:873','127.0.0.1:'+str(backend.server_address[1]))
(root/'nginx.conf').write_text(f'load_module {module};\ndaemon off;\nworker_processes 2;\npid {root}/nginx.pid;\nerror_log {root}/error.log;\nevents {{ worker_connections 128; }}\nstream {{\njs_var $rsync_forbidden 0;\n'+example+'\n}\n')
p=subprocess.Popen(['/usr/sbin/nginx','-p',str(root)+'/', '-c',str(root/'nginx.conf'),'-e',str(root/'startup.log')])
clients=[]
def receive_until(client,needle):
    data=b''; deadline=time.monotonic()+8
    while needle not in data and time.monotonic()<deadline:
        try: chunk=client.recv(4096)
        except socket.timeout: continue
        if not chunk: break
        data+=chunk
    assert needle in data, repr(data)
    return data

def connect():
    client=socket.create_connection(('127.0.0.1',18873),timeout=1)
    clients.append(client)
    receive_until(client,b'@RSYNCD: 31.0\n')
    client.sendall(b'@RSYNCD: 31.0\nubuntu\n')
    return client
try:
    time.sleep(.4)
    assert p.poll() is None, '\n'.join(f.read_text() for f in root.glob('*.log'))
    a=connect(); receive_until(a,b'@RSYNCD: OK')
    b=connect(); receive_until(b,b'Your position: 1')
    c=connect(); receive_until(c,b'queue is full'); c.close()
    time.sleep(4)  # Active lease must survive beyond its 3-second TTL.
    b.settimeout(.2)
    try:
        pending=b.recv(4096)
        assert b'@RSYNCD: OK' not in pending and b'@ERROR' not in pending, repr(pending)
    except socket.timeout: pass
    b.settimeout(1)
    a.close(); receive_until(b,b'@RSYNCD: OK'); b.close()
    time.sleep(.4)
    d=connect(); receive_until(d,b'@RSYNCD: OK'); d.close()
    time.sleep(.4)
    access=(root/'access.log').read_text()
    assert 'queued=true initial_queue_position=1' in access, access
    assert 'status=429' in access, access
    print('PASS: preread greeting, shared queue, full rejection, TTL renewal, slot release, queue statistics')
finally:
    for client in clients: client.close()
    if p.poll() is None:
        p.send_signal(signal.SIGQUIT)
        try: p.wait(timeout=10)
        except subprocess.TimeoutExpired: p.kill(); p.wait()
    backend.shutdown(); backend.server_close()
