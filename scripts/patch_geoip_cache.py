#!/usr/bin/env python3
"""Independent source fix: invalidate cached MMDB entries on successful reload."""
import pathlib
import sys
for name in ['ngx_http_geoip2_module.c','ngx_stream_geoip2_module.c']:
 p=pathlib.Path(sys.argv[1])/name
 s=p.read_text()
 substitutions=[
 ('    MMDB_lookup_result_s     result;', '    MMDB_lookup_result_s     result;\n    ngx_flag_t               cache_valid;'),
 ('if (ngx_memcmp(&address, &database->address, sizeof(address))', 'if (!database->cache_valid || ngx_memcmp(&address, &database->address, sizeof(address))'),
 ('if (address != database->address)', 'if (!database->cache_valid || address != database->address)'),
 ('        if (mmdb_error != MMDB_SUCCESS) {','        database->cache_valid = (mmdb_error == MMDB_SUCCESS);\n        if (mmdb_error != MMDB_SUCCESS) {'),
 ('        database->mmdb = tmpdb;', '        database->mmdb = tmpdb;\n        database->cache_valid = 0;\n        ngx_memzero(&database->result, sizeof(database->result));')]
 for old,new in substitutions:
  if s.count(old)!=1: raise ValueError(f'{name}: expected exactly one {old!r}')
  s=s.replace(old,new)
 p.write_text(s)
