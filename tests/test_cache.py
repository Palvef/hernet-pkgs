import pathlib
import subprocess
import tempfile
import unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class CachePatchTests(unittest.TestCase):
 def test_http_and_stream_and_repeat_rejected(self):
  original='\n'.join(['    MMDB_lookup_result_s     result;','if (ngx_memcmp(&address, &database->address, sizeof(address))','if (address != database->address)','        if (mmdb_error != MMDB_SUCCESS) {','        database->mmdb = tmpdb;'])
  with tempfile.TemporaryDirectory() as d:
   for n in ['http','stream']:
    handler='\nstatic ngx_int_t\nngx_http_geoip2_log_handler(ngx_http_request_t *r)\n{ if (empty) { return NGX_OK; } return NGX_OK; }\nstatic ngx_int_t\nngx_http_geoip2_init(ngx_conf_t *cf)\n{ return NGX_OK; }' if n=='http' else ''
    (pathlib.Path(d)/('ngx_'+n+'_geoip2_module.c')).write_text(original+handler)
   subprocess.run(['python3',str(ROOT/'scripts/patch_geoip_cache.py'),d],check=True)
   for n in ['http','stream']:
    data=(pathlib.Path(d)/('ngx_'+n+'_geoip2_module.c')).read_text()
    self.assertIn('database->cache_valid = 0;',data)
    self.assertIn('!database->cache_valid ||',data)
    if n=='http':
     self.assertEqual(data.count('return NGX_DECLINED;'),2)
     self.assertIn('ngx_http_geoip2_init(ngx_conf_t *cf)\n{ return NGX_OK; }',data)
   self.assertNotEqual(subprocess.run(['python3',str(ROOT/'scripts/patch_geoip_cache.py'),d],capture_output=True).returncode,0)
