"""Public independent module package names, dependencies, and migration policy."""
MODULES={
 'nginx-module-ndk-ha':'ndk_http_module.so',
 'nginx-module-lua-ha':'ngx_http_lua_module.so',
 'nginx-module-fancyindex-ha':'ngx_http_fancyindex_module.so',
 'nginx-module-http-geoip2-ha':'ngx_http_geoip2_module.so',
 'nginx-module-stream-geoip2-ha':'ngx_stream_geoip2_module.so',
 'nginx-module-vts-ha':'ngx_http_vhost_traffic_status_module.so',
 'nginx-module-http-njs-ha':'ngx_http_js_module.so',
 'nginx-module-stream-njs-ha':'ngx_stream_js_module.so'}

def dependencies(name,nginx_version,package_version,shared_libraries):
 deps=list(shared_libraries)
 if name in MODULES: deps.insert(0,f'nginx (= {nginx_version})')
 if name=='nginx-module-lua-ha':
  deps += [f'nginx-module-ndk-ha (= {package_version})',f'nginx-lua-libraries-ha (= {package_version})']
 return deps

def module_directory(nginx_version,revision):
 return f'/usr/lib/nginx/ha-modules/{nginx_version}/hernet-1.0.3-r{revision}'
