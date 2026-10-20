import sys
from pathlib import Path
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from prepare_pages import export

class ExportTests(unittest.TestCase):
    def test_only_public_repository_files(self):
        keep=['index.html','install.txt','lua-dependencies.txt','hernet-pkgs.gpg','mainline/index.html','mainline/debian/index.html','mainline/debian/pool/test/bookworm/module.deb','mainline/debian/dists/bookworm/InRelease','mainline/debian/dists/bookworm/main/binary-amd64/Packages.gz']
        omit=['CNAME','.git/config','releases.json','iptv-rtmp.md','mainline/debian/CNAME','mainline/debian/pool/test/build.log','mainline/debian/dists/bookworm/evidence/1.31.7/index.html','mainline/debian/dists/bookworm/evidence/1.31.7/build.log']
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);source=root/'source'
            for name in keep+omit:
                p=source/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('test')
            dest=root/'public';export(source,dest)
            self.assertEqual({p.relative_to(dest).as_posix() for p in dest.rglob('*') if p.is_file()},set(keep))
