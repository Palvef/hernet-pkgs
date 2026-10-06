import importlib.util
import pathlib
import tempfile
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
class PatchTests(unittest.TestCase):
    def test_symbol_bounded_patch(self):
        with tempfile.TemporaryDirectory() as d:
            d=pathlib.Path(d)
            (d/'m.c').write_text('void ngx_http_geoip2_init(void) { __asm__(".byte 0x48,0x81,0xc7,0x78,0x02,0,0"); } void unrelated(void) { __asm__(".byte 0x48,0x81,0xc7,0x78,0x02,0,0"); }')
            subprocess.run(['cc','-shared','-fPIC',str(d/'m.c'),'-o',str(d/'m.so')],check=True)
            subprocess.run(['python3',str(ROOT/'scripts/patch_geoip.py'),str(d/'m.so')],check=True)
            data=(d/'m.so').read_bytes()
            self.assertEqual(data.count(bytes.fromhex('48 81 c7 78 02 00 00')),1)
            self.assertEqual(data.count(bytes.fromhex('48 81 c7 e8 00 00 00')),1)
            result=subprocess.run(['python3',str(ROOT/'scripts/patch_geoip.py'),str(d/'m.so')],capture_output=True)
            self.assertNotEqual(result.returncode,0)
if __name__=='__main__': unittest.main()
