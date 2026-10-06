#!/usr/bin/env python3
"""Source fixes: invalidate reloaded MMDB cache and continue POST_READ handlers."""
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
 if name=='ngx_http_geoip2_module.c':
  start=s.index('\nngx_http_geoip2_log_handler(ngx_http_request_t *r)\n{')
  end=s.index('\nstatic ngx_int_t\nngx_http_geoip2_init',start)
  handler=s[start:end]
  if handler.count('return NGX_OK;')!=2: raise ValueError('Expected two HTTP handler success returns')
  # POST_READ must continue to other handlers, especially the RealIP handler.
  s=s[:start]+handler.replace('return NGX_OK;','return NGX_DECLINED;')+s[end:]
 p.write_text(s)
