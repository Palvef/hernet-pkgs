#!/usr/bin/env python3
import os
import pathlib
import subprocess
pv=os.environ['pv']
expected={'ndk_http_module.so','ngx_http_lua_module.so','ngx_http_fancyindex_module.so','ngx_http_geoip2_module.so','ngx_stream_geoip2_module.so','ngx_http_vhost_traffic_status_module.so','ngx_http_js_module.so','ngx_stream_js_module.so'}
found=set()
for p in pathlib.Path('/out').glob('*.deb'):
 name=subprocess.check_output(['dpkg-deb','-f',str(p),'Package'],text=True).strip()
 dep=subprocess.check_output(['dpkg-deb','-f',str(p),'Depends'],text=True).strip()
 if name.startswith('nginx-module-'):
  assert f'nginx (= {pv})' in dep,(name,dep)
  listing=subprocess.check_output(['dpkg-deb','-c',str(p)],text=True)
  for line in listing.splitlines():
   if line.endswith('.so'):
    file=line.split()[-1]
    assert '/usr/lib/nginx/ha-modules/'+pv+'/' in file,file
    found.add(pathlib.PurePosixPath(file).name)
assert found==expected,(found,expected)
print('PASS: all eight version-isolated modules have exact official NGINX dependencies')
