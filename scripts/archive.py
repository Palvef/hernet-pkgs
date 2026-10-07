#!/usr/bin/env python3
"""Verify byte-preserving migration, then clean obsolete repository layouts."""
import hashlib
import pathlib
import shutil
import subprocess
import sys
import json

SUITES=['bookworm','trixie','jammy','noble','resolute']
SLUGS=['ndk','lua','fancyindex','http-geoip2','stream-geoip2','vts','http-njs','stream-njs']
PACKAGES={'nginx-module-'+slug+'-ha' for slug in SLUGS}|{'nginx-lua-libraries-ha','njs-cli-ha'}
RTMP_PACKAGES={'nginx-module-rtmp-ha', 'nginx-module-stream-ha'}

def digest(path): return hashlib.sha256(path.read_bytes()).digest()

def copy_immutable(source,dest):
    dest.parent.mkdir(parents=True,exist_ok=True)
    checksum=digest(source)
    if dest.exists() and checksum!=digest(dest):
        raise ValueError('Immutable artifact collision: '+str(dest))
    if source.resolve()!=dest.resolve(): shutil.copy2(source,dest)
    if digest(dest)!=checksum: raise ValueError('Migration checksum mismatch: '+str(dest))

def package_directory(name,suite):
    if name not in PACKAGES | RTMP_PACKAGES or suite not in SUITES: raise ValueError('Unknown package or suite: '+name+' '+suite)
    slug=name.removeprefix('nginx-module-').removesuffix('-ha')
    if name=='nginx-lua-libraries-ha': slug='lua-libraries'
    if name=='njs-cli-ha': slug='njs-cli'
    return pathlib.Path('pool')/slug/suite

def download_indexes(site):
    import html
    root=site/'pool'
    if not root.exists(): return
    for folder in sorted([root,*root.rglob('*')],reverse=True):
        if not folder.is_dir(): continue
        links=[]
        for child in sorted(folder.iterdir()):
            if child.name=='index.html': continue
            if child.is_dir() or child.suffix=='.deb':
                name=child.name+('/' if child.is_dir() else '')
                links.append(f'<li><a href="{html.escape(name)}">{html.escape(name)}</a></li>')
        (folder/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>HerNet downloads</title><h1>'+html.escape(folder.relative_to(site).as_posix())+'</h1><ul>'+''.join(links)+'</ul>')

def archive(artifacts,site):
    retained={}
    def register(source,suite):
        name=source.name.split('_',1)[0]
        dest=package_directory(name,suite)/source.name
        if dest in retained and digest(retained[dest])!=digest(source):
            raise ValueError('Conflicting migration inputs: '+str(dest))
        retained[dest]=source

    # Preflight every new target before cleanup. Missing or partial builds must
    # never remove previously published valid payloads.
    for suite in SUITES:
        source=artifacts/('packages-'+suite)
        availability=source/'availability.json'
        if not availability.exists(): raise ValueError('Missing availability: '+suite)
        status=json.loads(availability.read_text())['status']
        packages=list(source.glob('*.deb'))
        if status=='available' and {p.name.split('_',1)[0] for p in packages}!=PACKAGES:
            raise ValueError('Incomplete split package set: '+suite)
        if status not in ['available','unavailable']: raise ValueError('Unknown availability: '+suite)
        for p in packages: register(p,suite)

    # Retain all valid independent releases >=1.0.3 while removing the explicitly
    # deprecated 1.0.2 aggregate layout. Copy bytes before deleting any old tree.
    for family in ['modules','dependencies','tools','pool']:
        for p in (site/family).rglob('*.deb'):
            parts=p.name.split('_')
            if len(parts)!=3 or parts[0] not in PACKAGES | RTMP_PACKAGES: continue
            if subprocess.run(['dpkg','--compare-versions',parts[1],'ge','1.0.3'],check=False).returncode: continue
            register(p,p.parent.name)
    for dest,source in retained.items(): copy_immutable(source,site/dest)
    for dest,source in retained.items():
        if digest(site/dest)!=digest(source): raise ValueError('Unverified destination: '+str(dest))

    for suite in SUITES:
        evidence=site/'dists'/suite/'evidence';evidence.mkdir(parents=True,exist_ok=True)
        old=site/'evidence'/suite
        if old.exists(): shutil.copytree(old,evidence,dirs_exist_ok=True)
        for p in (artifacts/('packages-'+suite)).iterdir():
            if p.is_file() and p.suffix!='.deb': shutil.copy2(p,evidence/p.name)

    # Cleanup is deliberately authorized: every surviving current DEB above is
    # hash-verified at its canonical pool path before the old directories vanish.
    for family in ['modules','dependencies','tools','evidence']:
        if (site/family).exists(): shutil.rmtree(site/family)
    pool=site/'pool';pool.mkdir(exist_ok=True)
    for p in pool.rglob('*.deb'):
        if p.relative_to(site) not in retained: p.unlink()
    for p in pool.rglob('index.html'): p.unlink()
    for folder in sorted(pool.rglob('*'),key=lambda p:len(p.parts),reverse=True):
        if folder.is_dir() and not any(folder.iterdir()): folder.rmdir()
    download_indexes(site)
def archive_rtmp(artifacts,site):
    """Append independently tested RTMP packages without rebuilding other modules."""
    pending=[]
    for suite in SUITES:
        source=artifacts/('rtmp-'+suite)
        status=json.loads((source/'availability.json').read_text())['status']
        packages=list(source.glob('*.deb'))
        names={p.name.split('_',1)[0] for p in packages}
        if status not in ['available','unavailable']:
            raise ValueError('Unknown availability: '+suite)
        if status=='available' and names!=RTMP_PACKAGES:
            raise ValueError('Incomplete RTMP package set: '+suite)
        if status=='unavailable' and packages:
            raise ValueError('Unavailable target has packages: '+suite)
        for package in packages:
            dest=site/package_directory(package.name.split('_',1)[0],suite)/package.name
            if dest.exists() and digest(dest)!=digest(package):
                raise ValueError('Immutable artifact collision: '+str(dest))
            pending.append((package,dest))
    for source,dest in pending:
        copy_immutable(source,dest)
    for suite in SUITES:
        evidence=site/'dists'/suite/'evidence/rtmp'
        evidence.mkdir(parents=True,exist_ok=True)
        for p in (artifacts/('rtmp-'+suite)).iterdir():
            if p.is_file() and p.suffix!='.deb': shutil.copy2(p,evidence/p.name)
    download_indexes(site)

if __name__=='__main__':
    operation=archive_rtmp if '--rtmp' in sys.argv[3:] else archive
    operation(pathlib.Path(sys.argv[1]),pathlib.Path(sys.argv[2]))
