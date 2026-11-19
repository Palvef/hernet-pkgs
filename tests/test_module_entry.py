import importlib.util
import pathlib
import shutil
import subprocess
import tempfile
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('layout',ROOT/'scripts/package_layout.py')
layout=importlib.util.module_from_spec(spec);spec.loader.exec_module(layout)

class ModuleEntryTests(unittest.TestCase):
 def test_each_package_owns_its_stable_alias(self):
  with tempfile.TemporaryDirectory() as tmp:
   base=pathlib.Path(tmp)
   for name,module in layout.MODULES.items():
    source=base/module;source.write_bytes(name.encode())
    root=base/name
    layout.install_module_payload(root,source,layout.module_directory('1.31.9-1~noble','2'))
    alias=root/'usr/lib/nginx/ha-modules/active'/module
    self.assertTrue(alias.is_symlink())
    self.assertEqual(alias.read_bytes(),name.encode())
    self.assertFalse(alias.readlink().is_absolute())
    self.assertEqual(len(list(alias.parent.iterdir())),1)

 @unittest.skipUnless(shutil.which('dpkg') and shutil.which('dpkg-deb'),'requires dpkg')
 def test_real_dpkg_upgrade_replaces_alias_and_removes_old_payload(self):
  with tempfile.TemporaryDirectory() as tmp:
   base=pathlib.Path(tmp);root=base/'system';state=root/'var/lib/dpkg';state.mkdir(parents=True);(state/'status').touch()
   alias=root/'usr/lib/nginx/ha-modules/active/ngx_http_lua_module.so'
   for revision,nginx in [('1','1.31.8-1~noble'),('2','1.31.9-1~noble')]:
    package=base/('package'+revision);control=package/'DEBIAN';control.mkdir(parents=True)
    (control/'control').write_text(f'Package: test-ha-module\nVersion: {revision}\nArchitecture: all\nMaintainer: Test <test@example.com>\nDescription: stable module entry fixture\n')
    source=base/'ngx_http_lua_module.so';source.write_text(nginx)
    layout.install_module_payload(package,source,layout.module_directory(nginx,revision))
    deb=base/(revision+'.deb')
    subprocess.run(['dpkg-deb','--build','--root-owner-group',str(package),str(deb)],check=True,stdout=subprocess.DEVNULL)
    subprocess.run(['dpkg','--root='+str(root),'--force-not-root','--unpack',str(deb)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    self.assertEqual(alias.read_text(),nginx)
   self.assertFalse((root/layout.module_directory('1.31.8-1~noble','1').lstrip('/')).exists())
