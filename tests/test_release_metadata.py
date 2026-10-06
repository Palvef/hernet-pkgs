import pathlib
import shutil
import subprocess
import tempfile
import unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class ReleaseMetadataTests(unittest.TestCase):
 @unittest.skipUnless(shutil.which('apt-ftparchive'),'apt-utils required for Release generation test')
 def test_repeated_release_has_no_stale_self_checksum(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);dist=root/'dists/noble';packages=dist/'main/binary-amd64/Packages'
   packages.parent.mkdir(parents=True);packages.write_text('Package: fixture\nVersion: 1\nArchitecture: amd64\n\n')
   (dist/'Release').write_text('old repository Release\n')
   for _ in range(2):
    subprocess.run(['bash',str(ROOT/'scripts/release.sh'),str(root),'noble'],check=True)
    release=(dist/'Release').read_text()
    entries=release.split('SHA256:\n',1)[1].split('SHA512:',1)[0].splitlines()
    self.assertEqual([l.split()[-1] for l in entries],['main/binary-amd64/Packages'])
