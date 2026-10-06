import pathlib
import subprocess
import tempfile
import unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class CachePatchTests(unittest.TestCase):
 def test_http_and_stream_and_repeat_rejected(self):
  original='\n'.join(['    MMDB_lookup_result_s     result;','if (ngx_memcmp(&address, &database->address, sizeof(address))','if (address != database->address)','        if (mmdb_error != MMDB_SUCCESS) {','        database->mmdb = tmpdb;'])
  with tempfile.TemporaryDirectory() as d:
   for n in ['http','stream']: (pathlib.Path(d)/('ngx_'+n+'_geoip2_module.c')).write_text(original)
   subprocess.run(['python3',str(ROOT/'scripts/patch_geoip_cache.py'),d],check=True)
   for n in ['http','stream']:
    data=(pathlib.Path(d)/('ngx_'+n+'_geoip2_module.c')).read_text()
    self.assertIn('database->cache_valid = 0;',data)
    self.assertIn('!database->cache_valid ||',data)
   self.assertNotEqual(subprocess.run(['python3',str(ROOT/'scripts/patch_geoip_cache.py'),d],capture_output=True).returncode,0)
