#!/usr/bin/env python3
"""Export only the public package repository and installation interface."""
from pathlib import Path
import shutil
import sys

ROOT_FILES = {'index.html', 'hernet-pkgs.asc', 'hernet-pkgs.gpg', 'install.txt', 'lua-dependencies.txt'}
APT_FILES = {'index.html', 'Packages', 'Packages.gz', 'Release', 'Release.gpg', 'InRelease'}

def export(source, dest):
    if dest.exists():
        raise ValueError('Export destination must be new')
    dest.mkdir(parents=True)
    for p in source.rglob('*'):
        if not p.is_file() or p.is_symlink():
            continue
        rel = p.relative_to(source)
        parts = rel.parts
        allowed = len(parts) == 1 and p.name in ROOT_FILES
        if len(parts) >= 3 and parts[0] == 'mainline' and parts[1] in {'debian', 'ubuntu'}:
            if parts[2] == 'pool':
                allowed = p.name == 'index.html' or p.suffix == '.deb'
            elif parts[2] == 'dists':
                allowed = p.name in APT_FILES and 'evidence' not in parts
            elif len(parts) == 3 and p.name == 'index.html':
                allowed = True
        if parts == ('mainline', 'index.html'):
            allowed = True
        if allowed:
            target=dest/rel
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(p,target)

if __name__ == '__main__':
    export(Path(sys.argv[1]),Path(sys.argv[2]))
