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

def archive(artifacts,site):
    for suite in ['bookworm','trixie','jammy','noble','resolute']:
        (site/'pool'/suite).mkdir(parents=True,exist_ok=True)
        source=artifacts/('packages-'+suite)
        if not (source/'availability.json').exists(): raise ValueError('Missing availability: '+suite)
        for p in source.glob('*.deb'): copy_immutable(p,site/'pool'/suite/p.name)
        evidence=site/'evidence'/suite
        evidence.mkdir(parents=True,exist_ok=True)
        for p in source.iterdir():
            if p.is_file() and p.suffix!='.deb': shutil.copy2(p,evidence/p.name)
if __name__=='__main__': archive(pathlib.Path(sys.argv[1]),pathlib.Path(sys.argv[2]))
