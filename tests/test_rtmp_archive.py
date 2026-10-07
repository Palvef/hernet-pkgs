import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('archive', ROOT / 'scripts/archive.py')
archive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive)


class RTMPArchiveTests(unittest.TestCase):
    def fixtures(self, root):
        artifacts, site = root / 'artifacts', root / 'site'
        existing = site / 'pool/lua/noble/nginx-module-lua-ha_1.0.3-existing_amd64.deb'
        existing.parent.mkdir(parents=True)
        existing.write_bytes(b'existing production release')
        for suite in archive.SUITES:
            folder = artifacts / ('rtmp-' + suite)
            folder.mkdir(parents=True)
            (folder / 'availability.json').write_text(json.dumps({'status': 'available'}))
            for name in ['nginx-module-rtmp-ha', 'nginx-module-stream-ha']:
                (folder / (name + '_1.0.3+nginx1.31.6-1_amd64.deb')).write_bytes((suite + name).encode())
        return artifacts, site, existing

    def test_addon_preserves_other_packages(self):
        with tempfile.TemporaryDirectory() as directory:
            artifacts, site, existing = self.fixtures(Path(directory))
            archive.archive_rtmp(artifacts, site)
            self.assertEqual(existing.read_bytes(), b'existing production release')
            self.assertEqual(len(list(site.rglob('*.deb'))), 11)
            self.assertTrue((site / 'pool/rtmp/noble/index.html').exists())
            self.assertTrue((site / 'dists/noble/evidence/rtmp/availability.json').exists())

    def test_incomplete_addon_cannot_publish(self):
        with tempfile.TemporaryDirectory() as directory:
            artifacts, site, existing = self.fixtures(Path(directory))
            next((artifacts / 'rtmp-noble').glob('nginx-module-stream*.deb')).unlink()
            with self.assertRaises(ValueError):
                archive.archive_rtmp(artifacts, site)
            self.assertEqual(existing.read_bytes(), b'existing production release')
            self.assertEqual(len(list(site.rglob('*.deb'))), 1)

    def test_regular_module_publication_retains_rtmp_addon(self):
        with tempfile.TemporaryDirectory() as directory:
            artifacts, site, existing = self.fixtures(Path(directory))
            archive.archive_rtmp(artifacts, site)
            for suite in archive.SUITES:
                folder = artifacts / ('packages-' + suite)
                folder.mkdir()
                (folder / 'availability.json').write_text(json.dumps({'status': 'unavailable'}))
            archive.archive(artifacts, site)
            self.assertEqual(existing.read_bytes(), b'existing production release')
            self.assertEqual(len(list(site.rglob('*.deb'))), 11)
