#!/usr/bin/env python3
import json
import os
from pathlib import Path
import shutil
import subprocess
from package_layout import MODULES, dependencies, module_directory
v,pv=os.environ['NGINX_VERSION'],os.environ['pv']
rel=dict(line.strip().split('=',1) for line in Path('/etc/os-release').read_text().splitlines() if '=' in line)['VERSION_CODENAME'].strip('"')
objs=Path('/work/nginx-'+v+'/objs'); base=Path('/work/packages')
groups={name:[module] for name,module in MODULES.items()}
groups.update({'njs-cli-ha':[], 'nginx-lua-libraries-ha':[]})
lock=json.loads(Path('/repo/sources.json').read_text())
for name,files in groups.items():
 root=base/name; root.mkdir(parents=True)
 if files:
  dest=root/module_directory(pv,os.environ.get('BUILD_REVISION','1')).lstrip('/'); dest.mkdir(parents=True)
  for f in files: shutil.copy2(objs/f,dest/f)
 if name=='njs-cli-ha':
  (root/'usr/bin').mkdir(parents=True); shutil.copy2('/work/sources/njs/build/njs',root/'usr/bin/njs-ha')
 if name=='nginx-lua-libraries-ha':
  lib=root/'usr/local/share/lua/5.1'; lib.mkdir(parents=True)
  for source in ['lua-resty-core','lua-resty-lrucache','lua-resty-redis']:
   shutil.copytree('/work/sources/'+source+'/lib',lib,dirs_exist_ok=True)
  clib=root/'usr/local/lib/lua/5.1'; clib.mkdir(parents=True)
  shutil.copy2('/work/sources/lua-cjson/cjson.so',clib/'cjson.so')
 binaries=list(root.rglob('*.so'))+list((root/'usr/bin').glob('*'))
 (root/'debian').mkdir(); (root/'debian/control').write_text('Source: hernet-modules\n\nPackage: '+name+'\nArchitecture: any\nDescription: HerNet modules\n')
 dep=subprocess.check_output(['dpkg-shlibdeps','-O',*['-e'+str(p) for p in binaries]],cwd=root,text=True).strip().removeprefix('shlibs:Depends=')
 version=f'1.0.3+git.a3aec77d+nginx{pv}-{os.environ.get("BUILD_REVISION","1")}'
 dep=', '.join(dependencies(name,pv,version,[d for d in dep.split(', ') if d]))
 (root/'DEBIAN').mkdir()
 (root/'DEBIAN/control').write_text(f'Package: {name}\nVersion: {version}\nArchitecture: amd64\nMaintainer: Palvef <packages@palve.moe>\nDepends: {dep}\nDescription: HerNet patched modules for official NGINX mainline\n')
 docs=root/('usr/share/doc/'+name); docs.mkdir(parents=True)
 (docs/'source-manifest.json').write_text(json.dumps(dict(sources=lock,nginx_package_version=pv,distribution=rel,patches=['geoip2-cache-valid-source','geoip2-http-log-to-post-read-binary','geoip2-http-post-read-continue-source']),indent=2)+'\n')
 shutil.copy2('/out/geoip2-patch.json',docs/'geoip2-patch.json')
 shutil.copy2('/out/geoip2-cache.patch',docs/'geoip2-cache.patch')
 for source in Path('/work/sources').iterdir():
  licenses=list(source.glob('*LICENSE*'))+list(source.glob('*COPYING*'))
  for license in licenses:
   if license.is_file(): shutil.copy2(license,docs/(source.name+'-'+license.name))
 # lua-nginx-module carries its license in its README.
 shutil.copy2('/work/sources/lua-nginx-module/README.markdown',docs/'lua-nginx-module-README.markdown')
 shutil.copy2('/work/nginx-'+v+'/LICENSE',docs/'nginx-LICENSE')
 shutil.rmtree(root/'debian')
 epoch=int(os.environ['SOURCE_DATE_EPOCH'])
 for item in root.rglob('*'):
  if not item.is_symlink(): os.utime(item,(epoch,epoch))
 os.utime(root,(epoch,epoch))
 subprocess.run(['dpkg-deb','--build','--root-owner-group',str(root),f'/out/{name}_{version}_amd64.deb'],check=True)
