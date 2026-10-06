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
