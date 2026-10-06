#!/usr/bin/env python3
"""Immutable package archive: reject same-name artifacts with different content."""
import hashlib
import pathlib
import shutil
import sys

def copy_immutable(source,dest):
    dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists() and hashlib.sha256(source.read_bytes()).digest()!=hashlib.sha256(dest.read_bytes()).digest():
        raise ValueError('Immutable artifact collision: '+str(dest))
    shutil.copy2(source,dest)

def package_directory(name,suite):
    if name.startswith('nginx-module-'):
        slug=name.removeprefix('nginx-module-').removesuffix('-ha')
        if slug not in ['ndk','lua','fancyindex','http-geoip2','stream-geoip2','vts','http-njs','stream-njs']:
            raise ValueError('Aggregate or unknown module package: '+name)
        return pathlib.Path('modules')/slug/suite
    if name=='nginx-lua-libraries-ha': return pathlib.Path('dependencies/lua-libraries')/suite
    if name=='njs-cli-ha': return pathlib.Path('tools/njs')/suite
    raise ValueError('Unknown package: '+name)

def download_indexes(site):
    import html
    for family in ['modules','dependencies','tools']:
        root=site/family
        if not root.exists(): continue
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
    for suite in ['bookworm','trixie','jammy','noble','resolute']:
        (site/'pool'/suite).mkdir(parents=True,exist_ok=True)
        source=artifacts/('packages-'+suite)
        if not (source/'availability.json').exists(): raise ValueError('Missing availability: '+suite)
        for p in source.glob('*.deb'):
            destination=package_directory(p.name.split('_',1)[0],suite)
            copy_immutable(p,site/destination/p.name)
        evidence=site/'evidence'/suite
        evidence.mkdir(parents=True,exist_ok=True)
        for p in source.iterdir():
            if p.is_file() and p.suffix!='.deb': shutil.copy2(p,evidence/p.name)
    download_indexes(site)
if __name__=='__main__': archive(pathlib.Path(sys.argv[1]),pathlib.Path(sys.argv[2]))
