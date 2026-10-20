#!/usr/bin/env python3
import html
from pathlib import Path
import sys
root=Path(sys.argv[1])
(root/'lua-dependencies.txt').write_text('Lua requires the matching nginx-module-ndk-ha and nginx-lua-libraries-ha packages. APT installs dependencies automatically.\n'+''.join('https://hernet-pkgs.palve.moe/'+p.relative_to(root).as_posix()+'\n' for p in sorted(root.glob('mainline/*/pool/*/*/*.deb')) if any(x in p.name for x in ['-lua-', '-ndk-'])))
(root/'install.txt').write_text('''# Debian / Ubuntu, NGINX official mainline > 1.31.6, amd64
curl -fsS https://hernet-pkgs.palve.moe/hernet-pkgs.gpg | sudo tee /usr/share/keyrings/hernet-pkgs.gpg >/dev/null
. /etc/os-release
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/hernet-pkgs.gpg] https://hernet-pkgs.palve.moe/mainline/$ID $VERSION_CODENAME main" | sudo tee /etc/apt/sources.list.d/hernet-pkgs.list
# Also configure the official NGINX mainline repository: https://nginx.org/en/linux_packages.html
sudo apt update
sudo apt install nginx-module-lua-ha nginx-module-http-njs-ha nginx-module-http-geoip2-ha
# Packages require the exact official NGINX package version used for the build.
''')

for folder in [root, root/'mainline', *(p for p in (root/'mainline').rglob('*') if p.is_dir())]:
    links=[]
    for p in sorted(folder.iterdir()):
        if p.name.startswith('.') or p.name == 'index.html': continue
        name=p.name+('/' if p.is_dir() else '')
        links.append(f'<li><a href="{html.escape(name)}">{html.escape(name)}</a></li>')
    title=folder.relative_to(root).as_posix()
    intro='<p>NGINX mainline &gt; 1.31.6; independent modules. <a href="install.txt">APT setup</a></p>' if folder==root else ''
    (folder/'index.html').write_text(f'<!doctype html><meta charset="utf-8"><title>HerNet {title}</title><h1>HerNet {title}</h1>{intro}<ul>'+''.join(links)+'</ul>')
