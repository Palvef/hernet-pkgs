import importlib.util
import pathlib
import unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('layout',ROOT/'scripts/package_layout.py')
layout=importlib.util.module_from_spec(spec);spec.loader.exec_module(layout)
class PackageLayoutTests(unittest.TestCase):
 def test_independent_module_payloads(self):
  wanted={
   'nginx-module-ndk-ha':'ndk_http_module.so',
   'nginx-module-lua-ha':'ngx_http_lua_module.so',
   'nginx-module-fancyindex-ha':'ngx_http_fancyindex_module.so',
   'nginx-module-http-geoip2-ha':'ngx_http_geoip2_module.so',
   'nginx-module-stream-geoip2-ha':'ngx_stream_geoip2_module.so',
   'nginx-module-vts-ha':'ngx_http_vhost_traffic_status_module.so',
   'nginx-module-http-njs-ha':'ngx_http_js_module.so',
   'nginx-module-stream-njs-ha':'ngx_stream_js_module.so'}
  self.assertEqual(layout.MODULES,wanted)
 def test_lua_installs_ndk_and_libraries(self):
  deps=layout.dependencies('nginx-module-lua-ha','1.31.6-1~noble','1.0.3-1',['libc6 (>= 2.34)'])
  self.assertIn('nginx (= 1.31.6-1~noble)',deps)
  self.assertIn('nginx-module-ndk-ha (= 1.0.3-1)',deps)
  self.assertIn('nginx-lua-libraries-ha (= 1.0.3-1)',deps)
 def test_fancyindex_does_not_install_lua(self):
  deps=layout.dependencies('nginx-module-fancyindex-ha','1.31.6-1~noble','1.0.3-1',[])
  self.assertEqual(deps,['nginx (= 1.31.6-1~noble)'])
 def test_release_path_preserves_legacy_files(self):
  self.assertEqual(layout.module_directory('1.31.6-1~noble','2'),'/usr/lib/nginx/ha-modules/1.31.6-1~noble/hernet-1.0.3-r2')
