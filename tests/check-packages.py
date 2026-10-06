#!/usr/bin/env python3
import os
import pathlib
import subprocess
import sys
sys.path.insert(0,'/repo/scripts')
from package_layout import MODULES,module_directory
pv=os.environ['pv']
found={}
for p in pathlib.Path('/out').glob('*.deb'):
 name=subprocess.check_output(['dpkg-deb','-f',str(p),'Package'],text=True).strip()
 dep=subprocess.check_output(['dpkg-deb','-f',str(p),'Depends'],text=True).strip()
 version=subprocess.check_output(['dpkg-deb','-f',str(p),'Version'],text=True).strip()
 assert name not in ['nginx-module-extras-ha','nginx-module-njs-ha'],name
 if name in MODULES:
  assert name not in found,name
  assert f'nginx (= {pv})' in dep,(name,dep)
  listing=subprocess.check_output(['dpkg-deb','-c',str(p)],text=True)
  modules=[]
  for line in listing.splitlines():
   if line.endswith('.so'):
    file=line.split()[-1]
    assert file=='.'+module_directory(pv,os.environ.get('BUILD_REVISION','1'))+'/'+MODULES[name],file
    modules.append(pathlib.PurePosixPath(file).name)
  assert modules==[MODULES[name]],(name,modules)
  found[name]=modules[0]
  for field in ['Breaks','Replaces','Conflicts']:
   relation=subprocess.check_output(['dpkg-deb','-f',str(p),field],text=True).strip()
   assert not relation,(name,field,relation)
  if name=='nginx-module-lua-ha':
   assert f'nginx-module-ndk-ha (= {version})' in dep,dep
   assert f'nginx-lua-libraries-ha (= {version})' in dep,dep
  else:
   assert 'nginx-module-lua-ha' not in dep and 'nginx-lua-libraries-ha' not in dep,(name,dep)
assert found==MODULES,(found,MODULES)
print('PASS: eight independent module DEBs, exact NGINX dependencies, Lua/NDK dependency and legacy coexistence policy')
