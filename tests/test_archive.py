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
  self.assertEqual(m.package_directory('nginx-module-lua-ha','noble'),pathlib.Path('modules/lua/noble'))
  self.assertEqual(m.package_directory('nginx-module-http-njs-ha','bookworm'),pathlib.Path('modules/http-njs/bookworm'))
  self.assertEqual(m.package_directory('nginx-lua-libraries-ha','trixie'),pathlib.Path('dependencies/lua-libraries/trixie'))
  self.assertEqual(m.package_directory('njs-cli-ha','jammy'),pathlib.Path('tools/njs/jammy'))
  with self.assertRaises(ValueError): m.package_directory('nginx-module-extras-ha','noble')
 def test_browsable_download_indexes(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d)
   package=root/'modules/lua/noble/module.deb'
   package.parent.mkdir(parents=True);package.write_bytes(b'fixture')
   m.download_indexes(root)
   self.assertIn('lua/',(root/'modules/index.html').read_text())
   self.assertIn('noble/',(root/'modules/lua/index.html').read_text())
   self.assertIn('module.deb',(root/'modules/lua/noble/index.html').read_text())
