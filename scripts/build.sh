#!/bin/bash
set -euo pipefail
[[ -f /.dockerenv && -d /repo ]] || { echo 'Disposable container required' >&2; exit 1; }
export DEBIAN_FRONTEND=noninteractive
. /etc/os-release
: "${NGINX_VERSION:=1.31.6}"
mkdir -p /work /out
cd /work
printf '#!/bin/sh\nexit 101\n' > /usr/sbin/policy-rc.d
chmod 755 /usr/sbin/policy-rc.d
apt-get update
apt-get install -y --no-install-recommends libeatmydata1
export LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libeatmydata.so
apt-get install -y --no-install-recommends build-essential ca-certificates curl gnupg git python3 libssl-dev libpcre2-dev zlib1g-dev libxml2-dev libxslt1-dev libmaxminddb-dev libluajit-5.1-dev libperl-dev dpkg-dev binutils
curl -fsS https://nginx.org/keys/nginx_signing.key -o nginx.key
gpg --show-keys --with-colons nginx.key | grep -q '573BFD6B3D8FBC641079A6ABABF5BD827BD9BF62'
gpg --dearmor < nginx.key > /usr/share/keyrings/nginx-build.gpg
printf 'deb [signed-by=/usr/share/keyrings/nginx-build.gpg] https://nginx.org/packages/mainline/%s %s nginx\n' "$ID" "$VERSION_CODENAME" > /etc/apt/sources.list.d/nginx.list
apt-get update
pv=$(apt-cache madison nginx | awk -v v="$NGINX_VERSION-" '/nginx.org/ && index($3,v)==1 {print $3; exit}')
if [[ -z $pv ]]; then
 printf '{"status":"unavailable","distribution":"%s","nginx":"%s"}\n' "$VERSION_CODENAME" "$NGINX_VERSION" > /out/availability.json
 exit 0
fi
printf '{"status":"available","distribution":"%s","nginx_package_version":"%s"}\n' "$VERSION_CODENAME" "$pv" > /out/availability.json
apt-get install -y --no-install-recommends "nginx=$pv"
nginx -V > /out/nginx-build.txt 2>&1
python3 /repo/scripts/fetch_sources.py /work/sources
export SOURCE_DATE_EPOCH=$(git -C /work/sources/njs show -s --format=%ct HEAD)
python3 /repo/scripts/patch_geoip_cache.py /work/sources/ngx_http_geoip2_module
(cd /work/sources/ngx_http_geoip2_module && git diff > /out/geoip2-cache.patch)
curl -fsS "https://nginx.org/download/nginx-$NGINX_VERSION.tar.gz" -o nginx.tar.gz
curl -fsS "https://nginx.org/download/nginx-$NGINX_VERSION.tar.gz.asc" -o nginx.tar.gz.asc
gpg --import nginx.key
curl -fsS https://nginx.org/keys/pluknet.key -o source.key
gpg --show-keys --with-colons source.key | grep -q D6786CE303D9A9022998DC6CC8464D549AF75C0A
gpg --import source.key
gpg --verify nginx.tar.gz.asc nginx.tar.gz
sha256sum nginx.tar.gz > /out/nginx-source.sha256
tar -xzf nginx.tar.gz
export LUAJIT_INC=/usr/include/luajit-2.1 LUAJIT_LIB=/usr/lib/x86_64-linux-gnu NJS_QUICKJS=NO
cd "/work/nginx-$NGINX_VERSION"
python3 - <<'PY'
import shlex,subprocess
args=shlex.split(subprocess.check_output(['nginx','-V'],stderr=subprocess.STDOUT).decode().split('configure arguments: ',1)[1])
mods=['ngx_devel_kit','lua-nginx-module','ngx-fancyindex','ngx_http_geoip2_module','nginx-module-vts','njs/nginx']
subprocess.run(['./configure',*args,*['--add-dynamic-module=/work/sources/'+m for m in mods]],check=True)
PY
make -j"$(nproc)" modules
python3 /repo/scripts/patch_geoip.py objs/ngx_http_geoip2_module.so > /out/geoip2-patch.json
cd /work/sources/njs
./configure --no-quickjs
make -j"$(nproc)" njs
make unit_test lib_test > /out/njs-tests.txt 2>&1
cd /work/sources/lua-cjson
make -j"$(nproc)" LUA_INCLUDE_DIR="$LUAJIT_INC"
export NGINX_VERSION pv
python3 /repo/scripts/package.py
python3 /repo/tests/check-packages.py > /out/package-check.txt
apt-get install -y --no-install-recommends /out/*.deb
export HA_MODULE_DIR="/usr/lib/nginx/ha-modules/$pv/hernet-1.0.3-r${BUILD_REVISION:-1}"
touch /work/MODULES_READY
python3 /repo/tests/runtime-smoke.py > /out/runtime-smoke.txt 2>&1
python3 /repo/tests/rsync-queue.py > /out/rsync-queue.txt 2>&1
python3 /repo/tests/geoip2-live.py --module-dir "$HA_MODULE_DIR" --empty /repo/tests/fixtures/empty.mmdb --populated /repo/tests/fixtures/populated.mmdb > /out/geoip2-live.txt 2>&1
(cd /out && sha256sum *.deb > SHA256SUMS)
