import importlib.util
import pathlib
import tempfile
import unittest
spec=importlib.util.spec_from_file_location('archive',pathlib.Path(__file__).resolve().parents[1]/'scripts/archive.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ArchiveTests(unittest.TestCase):
 def test_immutable_collision(self):
  with tempfile.TemporaryDirectory() as d:
   a,b=pathlib.Path(d)/'a',pathlib.Path(d)/'pool/b'
   a.write_bytes(b'one');m.copy_immutable(a,b);m.copy_immutable(a,b)
   a.write_bytes(b'two')
   with self.assertRaises(ValueError): m.copy_immutable(a,b)
   self.assertEqual(b.read_bytes(),b'one')
 def test_independent_download_directories(self):
  self.assertEqual(m.package_directory('nginx-module-lua-ha','noble'),pathlib.Path('pool/lua/noble'))
  self.assertEqual(m.package_directory('nginx-module-http-njs-ha','bookworm'),pathlib.Path('pool/http-njs/bookworm'))
  self.assertEqual(m.package_directory('nginx-lua-libraries-ha','trixie'),pathlib.Path('pool/lua-libraries/trixie'))
  self.assertEqual(m.package_directory('njs-cli-ha','jammy'),pathlib.Path('pool/njs-cli/jammy'))
  with self.assertRaises(ValueError): m.package_directory('nginx-module-extras-ha','noble')
 def test_browsable_download_indexes(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d)
   package=root/'pool/lua/noble/module.deb'
   package.parent.mkdir(parents=True);package.write_bytes(b'fixture')
   m.download_indexes(root)
   self.assertIn('lua/',(root/'pool/index.html').read_text())
   self.assertIn('noble/',(root/'pool/lua/index.html').read_text())
   self.assertIn('module.deb',(root/'pool/lua/noble/index.html').read_text())
 def test_dirty_legacy_site_migrates_verified_current_files_and_cleans_obsolete(self):
  import json
  names=['nginx-module-'+slug+'-ha' for slug in ['ndk','lua','fancyindex','http-geoip2','stream-geoip2','vts','http-njs','stream-njs']]+['nginx-lua-libraries-ha','njs-cli-ha']
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);site=root/'site';artifacts=root/'artifacts'
   for suite in ['bookworm','trixie','jammy','noble','resolute']:
    source=artifacts/('packages-'+suite);source.mkdir(parents=True)
    (source/'availability.json').write_text(json.dumps({'status':'available'}))
    for name in names:
     filename=name+'_1.0.3-test_amd64.deb';payload=(suite+' '+name).encode()
     (source/filename).write_bytes(payload)
     slug=name.removeprefix('nginx-module-').removesuffix('-ha')
     legacy=(site/'modules'/slug/suite if name.startswith('nginx-module-') else site/('dependencies/lua-libraries' if name=='nginx-lua-libraries-ha' else 'tools/njs')/suite)
     legacy.mkdir(parents=True);(legacy/filename).write_bytes(payload)
    obsolete=site/'pool'/suite;obsolete.mkdir(parents=True)
    (obsolete/'nginx-module-extras-ha_1.0.2-test_amd64.deb').write_bytes(b'old aggregate')
    (obsolete/'nginx-lua-libraries-ha_1.0.2-test_amd64.deb').write_bytes(b'old libraries')
   m.archive(artifacts,site)
   self.assertEqual(len(list((site/'pool').rglob('*.deb'))),50)
   for family in ['modules','dependencies','tools','evidence']:self.assertFalse((site/family).exists())
   self.assertFalse(any(p.name.startswith('nginx-module-extras-ha_') for p in site.rglob('*.deb')))
   for suite in ['bookworm','trixie','jammy','noble','resolute']:
    for name in names:
     filename=name+'_1.0.3-test_amd64.deb'
     self.assertEqual((site/m.package_directory(name,suite)/filename).read_bytes(),(suite+' '+name).encode())
    self.assertTrue((site/'dists'/suite/'evidence/availability.json').exists())
   m.archive(artifacts,site)
   self.assertEqual(len(list((site/'pool').rglob('*.deb'))),50)
 def test_migration_collision_preserves_original_and_obsolete_files(self):
  import json
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);site=root/'site';artifacts=root/'artifacts'
   for suite in ['bookworm','trixie','jammy','noble','resolute']:
    source=artifacts/('packages-'+suite);source.mkdir(parents=True)
    (source/'availability.json').write_text(json.dumps({'status':'unavailable'}))
   filename='nginx-module-lua-ha_1.0.3-test_amd64.deb'
   old=site/'modules/lua/noble'/filename;old.parent.mkdir(parents=True);old.write_bytes(b'old original')
   canonical=site/'pool/lua/noble'/filename;canonical.parent.mkdir(parents=True);canonical.write_bytes(b'conflicting destination')
   obsolete=site/'pool/noble/nginx-module-extras-ha_1.0.2-test_amd64.deb';obsolete.parent.mkdir(parents=True);obsolete.write_bytes(b'old aggregate')
   with self.assertRaises(ValueError):m.archive(artifacts,site)
   self.assertEqual(old.read_bytes(),b'old original')
   self.assertEqual(canonical.read_bytes(),b'conflicting destination')
   self.assertTrue(obsolete.exists())
