#!/usr/bin/env python3
import json
import pathlib
import subprocess
import sys
root=pathlib.Path(sys.argv[1]); root.mkdir(parents=True,exist_ok=True)
lock=json.loads(pathlib.Path('/repo/sources.json').read_text())
for name,src in lock.items():
    dest=root/name
    subprocess.run(['git','init',str(dest)],check=True)
    subprocess.run(['git','-C',str(dest),'fetch','--depth=1','https://github.com/'+src['repo']+'.git',src['commit']],check=True)
    subprocess.run(['git','-C',str(dest),'checkout','--detach','FETCH_HEAD'],check=True)
    actual=subprocess.check_output(['git','-C',str(dest),'rev-parse','HEAD'],text=True).strip()
    assert actual==src['commit'], name

# The clean pinned njs checkout hash excludes Git metadata.
import hashlib
h=hashlib.sha256(); njs=root/'njs'
for p in sorted(njs.rglob('*')):
    if p.is_file() and '.git' not in p.relative_to(njs).parts:
        h.update(p.relative_to(njs).as_posix().encode()+b'\0'+p.read_bytes()+b'\0')
if h.hexdigest()!='974de8770b284ff1a2befbcd004069dacba725077522c94bc79516f3991225ae':
    raise ValueError('njs tree differs from locked clean Git source hash: '+h.hexdigest())

# git archive honors export-ignore; authenticate the exact production archive too.
import io,tarfile
archive=subprocess.check_output(['git','-C',str(njs),'archive','HEAD'])
h=hashlib.sha256()
with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
    for member in sorted(tar.getmembers(),key=lambda m:m.name):
        if member.isfile():
            h.update(member.name.encode()+b'\0'+tar.extractfile(member).read()+b'\0')
if h.hexdigest()!='210cb681a7bb438f732deb07b19d3411dfad54188555c175c3daceceeaec594d':
    raise ValueError('njs archive differs from approved production input: '+h.hexdigest())
