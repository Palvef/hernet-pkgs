#!/usr/bin/env python3
"""Package RTMP and built-in stream dependencies; configuration remains separate."""
import json
import os
from pathlib import Path
import shutil
import subprocess

repo = Path('/repo')
pv = os.environ['pv']
revision = os.environ.get('RTMP_BUILD_REVISION', '1')
version = f'1.0.3+rtmp1.2.2+nginx{pv}-r{revision}'
module_dir = f'/usr/lib/nginx/ha-modules/{pv}/hernet-rtmp-1.0.3-r{revision}'
module = Path('/work/nginx-1.31.6/objs/ngx_rtmp_module.so')
epoch = int(os.environ['SOURCE_DATE_EPOCH'])
manifest = {
    'sources': json.loads((repo / 'rtmp-sources.json').read_text()),
    'nginx_package_version': pv,
    'module_directory': module_dir,
    'nginx_version': '1.31.6',
}

for name in ['nginx-module-rtmp-ha', 'nginx-module-stream-ha']:
    root = Path('/work/rtmp-packages') / name
    root.mkdir(parents=True)
    depends = f'nginx (= {pv})'
    if name == 'nginx-module-rtmp-ha':
        dest = root / module_dir.lstrip('/')
        dest.mkdir(parents=True)
        shutil.copy2(module, dest / module.name)
        (root / 'debian').mkdir()
        (root / 'debian/control').write_text(f'Source: hernet-rtmp\n\nPackage: {name}\nArchitecture: any\nDescription: RTMP module\n')
        libs = subprocess.check_output(['dpkg-shlibdeps', '-O', '-e' + str(dest / module.name)], cwd=root, text=True).strip().removeprefix('shlibs:Depends=')
        if libs:
            depends += ', ' + libs
        shutil.rmtree(root / 'debian')
    docs = root / 'usr/share/doc' / name
    docs.mkdir(parents=True)
    package_manifest = dict(manifest, package=name, delivery='dynamic-module' if name.endswith('rtmp-ha') else 'official-built-in-stream')
    if name.endswith('stream-ha'):
        package_manifest['module_directory'] = None
    (docs / 'source-manifest.json').write_text(json.dumps(package_manifest, indent=2) + '\n')
    shutil.copy2('/work/nginx-1.31.6/LICENSE', docs / 'nginx-LICENSE')
    shutil.copy2('/work/nginx-rtmp-module/LICENSE', docs / 'rtmp-LICENSE')
    shutil.copy2(repo / 'docs/iptv-rtmp.md', docs / 'README.md')
    control = root / 'DEBIAN'
    control.mkdir()
    description = 'RTMP and HLS dynamic module' if name.endswith('rtmp-ha') else 'Official built-in stream TCP UDP support for RTSP TCP forwarding'
    (control / 'control').write_text(f'Package: {name}\nVersion: {version}\nArchitecture: amd64\nMaintainer: Palvef <packages@palve.moe>\nDepends: {depends}\nDescription: {description} for official NGINX 1.31.6\n')
    for item in root.rglob('*'):
        if not item.is_symlink():
            os.utime(item, (epoch, epoch))
    os.utime(root, (epoch, epoch))
    subprocess.run(['dpkg-deb', '--build', '--root-owner-group', str(root), f'/out/{name}_{version}_amd64.deb'], check=True)
