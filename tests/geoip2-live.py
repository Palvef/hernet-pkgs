#!/usr/bin/env python3
"""Private two-worker integration; never uses or reloads production Nginx."""
import argparse,itertools,json,os,pathlib,shutil,socket,subprocess,tempfile,time,urllib.request,urllib.error
parser=argparse.ArgumentParser()
parser.add_argument('--nginx',default='/usr/sbin/nginx')
parser.add_argument('--module-dir',required=True)
parser.add_argument('--empty',required=True)
parser.add_argument('--populated',required=True)
parser.add_argument('--njs',help='Optional full candidate forbidden.njs')
parser.add_argument('--ipv4',default='198.51.100.10')
parser.add_argument('--ipv6',default='2001:4860::1')
parser.add_argument('--trusted-ipv4',default='127.0.0.1')
parser.add_argument('--trusted-ipv6',default='2001:da8:5018::1')
parser.add_argument('--reload-seconds',type=int,default=2)
args=parser.parse_args()
modules=pathlib.Path(args.module_dir).resolve()
empty=pathlib.Path(args.empty).resolve(); populated=pathlib.Path(args.populated).resolve()
assert empty.stat().st_size>0 and populated.stat().st_size>0
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args):return None
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
with tempfile.TemporaryDirectory(prefix='ban-dream-geoip2-') as directory:
    prefix=pathlib.Path(directory);prefix.chmod(0o755)
    database=prefix/'report.mmdb';shutil.copyfile(empty,database);database.chmod(0o644)
    with socket.socket() as listener:listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
    with socket.socket() as listener:listener.bind(('127.0.0.1',0));stream_port=listener.getsockname()[1]
    if args.njs:
        njs=prefix/'forbidden.njs';shutil.copyfile(args.njs,njs);njs.chmod(0o644)
    else:
        njs=prefix/'forbidden.njs'
        njs.write_text('''const crypto = require('crypto');
function fakehash(r) { return '00000091 ' + crypto.createHash('md5').update(r.remoteAddress+'|'+r.method+'|'+r.uri).digest('hex'); }
function forbidden(r) { r.headersOut['X-Block-Trace']=fakehash(r); r.return(403,'blocked'); }
export default {fakehash,forbidden};
''');njs.chmod(0o644)
    config=f'''load_module {modules}/ngx_http_geoip2_module.so;
load_module {modules}/ngx_http_js_module.so;
load_module {modules}/ngx_stream_geoip2_module.so;
worker_processes 2;
pid {prefix}/nginx.pid;
error_log {prefix}/error.log notice;
events {{ worker_connections 128; }}
http {{
set_real_ip_from 127.0.0.1;
set_real_ip_from ::1;
real_ip_header X-Test-Source;
geo $nyistnet {{ default 0; {args.trusted_ipv4}/32 1; {args.trusted_ipv6}/128 1; }}
geoip2 {database} {{ auto_reload {args.reload_seconds}s; $ban_dream_reason reasons_str; }}
map "$nyistnet|$ban_dream_reason" $ban_dream_deny {{ default 0; ~^0\\|.+ 1; }}
map $host $ban_dream_blocked {{ default 0; }}
map $host $force_403_ip {{ default 0; }}
map $http_user_agent $bad_user_agent {{ default 0; "curl/7.29.0" 1; }}
map $host $watch_403_ip {{ default 0; }}
map $host $badipua_ua {{ default 0; }}
map $host $badipua_large {{ default 0; }}
map $host $badipua_special {{ default 0; }}
js_import forbidden from '{njs}';
js_set $fakehash forbidden.fakehash;
map "$status|$ban_dream_blocked" $trace {{ "403|1" $fakehash; default ""; }}
log_format test escape=json '{{"worker":$pid,"address":"$remote_addr","status":$status,"reason":"$ban_dream_reason","trace":"$trace"}}';
access_log {prefix}/access.log test;
server {{
 listen 127.0.0.1:{port} reuseport;
 server_name mirror.nyist.edu.cn mirrors.ha.edu.cn mirror4.nyist.edu.cn mirror6.nyist.edu.cn mirrors.nyist.edu.cn mirrors4.ha.edu.cn mirrors6.ha.edu.cn mirror.ha.edu.cn;
 add_header X-Test-Worker $pid always;
 add_header X-Test-Address $remote_addr always;
 add_header X-Test-Reason $ban_dream_reason always;
 error_page 403 = @forbidden;
 set $ban_dream_blocked 0;
 if ($ban_dream_deny) {{ set $ban_dream_blocked 1; return 403; }}
 location @forbidden {{ js_content forbidden.forbidden; }}
 location = /redirect {{ return 302 /; }}
 location / {{ return 200 'allowed'; }}
}}
}}
'''
    config+=f'''stream {{
 geoip2 {database} {{ auto_reload {args.reload_seconds}s; $stream_reason reasons_str; }}
 server {{ listen 127.0.0.1:{stream_port} reuseport; return "$pid|$stream_reason"; }}
}}
'''
    configuration=prefix/'nginx.conf';configuration.write_text(config)
    check=subprocess.run([args.nginx,'-t','-p',str(prefix)+'/', '-c',str(configuration)],text=True,capture_output=True)
    if check.returncode:raise SystemExit(check.stdout+check.stderr)
    process=subprocess.Popen([args.nginx,'-p',str(prefix)+'/', '-c',str(configuration),'-g','daemon off;'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    counts=0;workers=set();public=[args.ipv4,args.ipv6];trusted=[args.trusted_ipv4,args.trusted_ipv6]
    def request(source,path='/',method='GET',host='mirror.nyist.edu.cn'):
        req=urllib.request.Request(f'http://127.0.0.1:{port}{path}',method=method,headers={'Host':host,'X-Test-Source':source,'User-Agent':'curl/7.29.0','Connection':'close'})
        try:response=opener.open(req,timeout=5)
        except urllib.error.HTTPError as error:response=error
        status=response.code;headers=response.headers;response.close()
        assert headers['X-Test-Address']==source, {"source":source,"status":status,"headers":dict(headers),"error_log":(prefix/"error.log").read_text()}
        workers.add(headers['X-Test-Worker'])
        return status,headers
    def stream_request():
        with socket.create_connection(('127.0.0.1',stream_port),timeout=5) as client:
            data=b''
            while True:
                part=client.recv(4096)
                if not part: break
                data+=part
        worker,reason=data.decode().split('|',1)
        return worker,bool(reason)
    def await_stream_phase(reason_expected):
        deadline=time.monotonic()+max(10,args.reload_seconds*4)
        converged={}
        while time.monotonic()<deadline:
            worker,has_reason=stream_request()
            if has_reason==reason_expected: converged[worker]=True
            else: converged.pop(worker,None)
            if len(converged)==2:return
            time.sleep(.03)
        raise AssertionError(f'stream workers did not converge: {reason_expected=} {converged=}')
    def replace(source):
        temporary=prefix/'next.mmdb';shutil.copyfile(source,temporary);temporary.chmod(0o644)
        stamp=max(time.time(),int(database.stat().st_mtime)+1);os.utime(temporary,(stamp,stamp));os.replace(temporary,database)
    def await_phase(expected,reason_expected):
        deadline=time.monotonic()+max(10,args.reload_seconds*4)
        converged={}
        while time.monotonic()<deadline:
            status,headers=request(args.ipv4)
            worker=headers['X-Test-Worker']
            if status==expected and bool(headers.get('X-Test-Reason'))==reason_expected:converged[worker]=True
            else:converged.pop(worker,None)
            if len(converged)==2:return
            time.sleep(.03)
        raise AssertionError(f'workers did not converge: {expected=} {converged=}')
    try:
        deadline=time.monotonic()+5
        while True:
            try:request(args.ipv4);break
            except OSError:
                if time.monotonic()>deadline:raise
                time.sleep(.05)
        # Same source lookup is repeated across atomic replacements without a
        # process reload; this detects a stale geoip2 same-IP cache in workers.
        for fixture,blocked in [(empty,False),(populated,True),(empty,False),(populated,True)]:
            replace(fixture);await_phase(403 if blocked else 200,blocked);await_stream_phase(blocked)
            for source,path,method,host in itertools.product(public+trusted,['/','/static/site.json','/debian/README','/redirect'],['GET','HEAD','POST','OPTIONS'],['mirror.nyist.edu.cn','mirrors.ha.edu.cn','mirror4.nyist.edu.cn','mirror.ha.edu.cn']):
                status,headers=request(source,path,method,host)
                should_block=blocked and source in public
                expected=403 if should_block else 302 if path=='/redirect' else 200
                assert status==expected,(source,path,method,status,expected,dict(headers))
                if should_block:assert headers['X-Block-Trace'].startswith('00000091 ')
                counts+=1
        # An invalid direct fixture replacement must leave each worker's last
        # valid database active. The updater prevents this in production.
        invalid=prefix/'invalid';invalid.write_bytes(b'not an MMDB');replace(invalid)
        time.sleep(args.reload_seconds+.2)
        for source in public:
            for _ in range(24):
                status,headers=request(source)
                assert status==403 and headers['X-Block-Trace'].startswith('00000091 ')
                counts+=1
        for _ in range(24): assert stream_request()[1], 'stream lost last valid database'
        assert len(workers)==2,workers
    finally:
        process.terminate();process.wait(timeout=10)
    logs=[json.loads(line) for line in (prefix/'access.log').read_text().splitlines()]
    assert any(item['trace'].startswith('00000091 ') and item['reason'] for item in logs)
    print(json.dumps({'checks':counts,'workers':len(workers),'realip_ipv4_ipv6':True,'trusted_exemption':True,'auto_reload_seconds':args.reload_seconds,'same_ip_empty_populated_invalidation':True,'stream_same_ip_invalidation':True,'invalid_replacement_preserves_active':True,'trace91_and_json':True}))
