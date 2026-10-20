import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from discover import eligible,newest
from archive_latest import publish
from archive import PACKAGES,RTMP_PACKAGES

class LatestTests(unittest.TestCase):
    def test_homepage_preserved(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'mainline/debian/pool').mkdir(parents=True)
            repo=Path(__file__).resolve().parents[1]
            subprocess.run([sys.executable,str(repo/'scripts/index_latest.py'),str(root)],check=True)
            self.assertEqual((root/'index.html').read_bytes(),(repo/'docs/index.html').read_bytes())
            self.assertTrue((root/'mainline/index.html').exists())
            self.assertIn('mainline/debian/pool/nginx-module-lua-ha/',(root/'index.html').read_text())
            self.assertNotIn('href="pool/',(root/'index.html').read_text())
    def test_floor(self):
        for v in ['1.31.6','1.31.6-2~noble','1.30.99','bad']:
            self.assertFalse(eligible(v))
        for v in ['1.31.7-1~noble','1.33.0']:
            self.assertTrue(eligible(v))
    def test_numeric_order_and_nginx_only(self):
        text='\n\n'.join(f'Package: nginx\nVersion: {v}' for v in ['1.31.6-1','1.31.9-1','1.31.10-1'])
        self.assertEqual(newest(text+'\n\nPackage: other\nVersion: 9.99.0'), '1.31.10-1')
    def test_empty_cleanup(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t); a=root/'a';s=root/'s';a.mkdir();s.mkdir()
            (s/'pool').mkdir();(s/'pool/old.deb').write_text('old')
            publish(a,s)
            self.assertFalse((s/'pool').exists())
            self.assertEqual(json.loads((s/'releases.json').read_text()),{})
    def test_incomplete_does_not_cleanup(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);a=root/'a';s=root/'s';(a/'packages-noble').mkdir(parents=True);(s/'pool').mkdir(parents=True)
            (s/'pool/old.deb').write_text('keep')
            (a/'packages-noble/target.json').write_text(json.dumps({'package':'1.31.7-1~noble'}))
            with self.assertRaises(ValueError): publish(a,s)
            self.assertTrue((s/'pool/old.deb').exists())
    def test_complete_set(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);a=root/'a';s=root/'s';source=a/'packages-noble';source.mkdir(parents=True);s.mkdir()
            (source/'target.json').write_text(json.dumps({'package':'1.31.7-1~noble'}))
            for name in PACKAGES|RTMP_PACKAGES:
                package=root/name;(package/'DEBIAN').mkdir(parents=True)
                version='1.0.3+nginx1.31.7-1~noble-r1'
                (package/'DEBIAN/control').write_text(f'Package: {name}\nVersion: {version}\nArchitecture: amd64\nMaintainer: Test <test@example.org>\nDescription: test\n')
                subprocess.run(['dpkg-deb','--build',str(package),str(source/f'{name}_{version}_amd64.deb')],check=True,stdout=subprocess.DEVNULL)
            publish(a,s)
            self.assertEqual(len(list((s/'mainline/ubuntu/pool').rglob('*.deb'))),12)
            self.assertEqual(json.loads((s/'releases.json').read_text())['noble']['package'],'1.31.7-1~noble')
            publish(a,s) # immutable repeat
if __name__=='__main__': unittest.main()
