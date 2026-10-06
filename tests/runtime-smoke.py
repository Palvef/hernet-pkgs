#!/usr/bin/env python3
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import urllib.request

version=os.environ.get('NGINX_VERSION','1.31.6')
objs=Path(os.environ.get('HA_MODULE_DIR','/work/nginx-'+version+'/objs'))
assert Path('/work/MODULES_READY').exists(), 'Run only after successful module linking'
root=Path(tempfile.mkdtemp(prefix='ha-module-runtime-'))
modules=['ndk_http_module','ngx_http_lua_module','ngx_http_fancyindex_module','ngx_http_geoip2_module','ngx_stream_geoip2_module','ngx_http_vhost_traffic_status_module','ngx_http_js_module','ngx_stream_js_module']
(root/'test.js').write_text('function hello(r) { r.return(200, "njs-ok"); } export default {hello};\n')
conf=''.join('load_module '+str(objs/(m+'.so'))+';\n' for m in modules)
conf+=f'''daemon off;
pid {root}/nginx.pid;
error_log {root}/error.log;
events {{ worker_connections 32; }}
http {{
 access_log off;
 js_import test from {root}/test.js;
 server {{
  listen 127.0.0.1:18081;
  location /lua {{ content_by_lua_block {{ assert(require("cjson").decode("true")); assert(require("resty.redis")); assert(require("resty.core")); ngx.say("lua-ok") }} }}
  location /njs {{ js_content test.hello; }}
 }}
}}
stream {{}}
'''
(root/'nginx.conf').write_text(conf)
p=subprocess.Popen(['/usr/sbin/nginx','-p',str(root)+'/', '-c',str(root/'nginx.conf'),'-e',str(root/'startup.log')])
try:
    for _ in range(100):
        if p.poll() is not None:
            raise RuntimeError('\n'.join(f.read_text() for f in root.glob('*.log')))
        try:
            with urllib.request.urlopen('http://127.0.0.1:18081/lua',timeout=1) as response:
                assert response.read().strip()==b'lua-ok'
            break
        except OSError: time.sleep(.1)
    else: raise RuntimeError('Lua endpoint not ready')
    with urllib.request.urlopen('http://127.0.0.1:18081/njs',timeout=1) as response:
        assert response.read()==b'njs-ok'
    print('PASS: official Nginx loads all modules and serves real Lua/njs requests')
finally:
    if p.poll() is None:
        p.send_signal(signal.SIGQUIT)
        try: p.wait(timeout=10)
        except subprocess.TimeoutExpired: p.kill(); p.wait()
