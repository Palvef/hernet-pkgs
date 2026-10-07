#!/bin/bash
set -euo pipefail
[[ -f /.dockerenv && -d /repo ]] || { echo 'Disposable container required' >&2; exit 1; }
export DEBIAN_FRONTEND=noninteractive
. /etc/os-release
mkdir -p /work /out
cd /work
printf '#!/bin/sh\nexit 101\n' > /usr/sbin/policy-rc.d
chmod 755 /usr/sbin/policy-rc.d
apt-get update
apt-get install -y --no-install-recommends build-essential ca-certificates curl gnupg git python3 libssl-dev libpcre2-dev zlib1g-dev dpkg-dev ffmpeg
curl -fsS https://nginx.org/keys/nginx_signing.key -o nginx.key
gpg --show-keys --with-colons nginx.key | grep -q '573BFD6B3D8FBC641079A6ABABF5BD827BD9BF62'
gpg --dearmor < nginx.key > /usr/share/keyrings/nginx-build.gpg
printf 'deb [signed-by=/usr/share/keyrings/nginx-build.gpg] https://nginx.org/packages/mainline/%s %s nginx\n' "$ID" "$VERSION_CODENAME" > /etc/apt/sources.list.d/nginx.list
apt-get update
pv=$(apt-cache madison nginx | awk '/nginx.org/ && index($3,"1.31.6-")==1 {print $3; exit}')
if [[ -z "$pv" ]]; then
 printf '{"status":"unavailable","distribution":"%s","nginx":"1.31.6"}\n' "$VERSION_CODENAME" > /out/availability.json
 exit 0
fi
export pv
printf '{"status":"available","distribution":"%s","nginx_package_version":"%s"}\n' "$VERSION_CODENAME" "$pv" > /out/availability.json
apt-get install -y --no-install-recommends "nginx=$pv"
nginx -V > /out/nginx-build.txt 2>&1
curl -fsS https://nginx.org/download/nginx-1.31.6.tar.gz -o nginx.tar.gz
curl -fsS https://nginx.org/download/nginx-1.31.6.tar.gz.asc -o nginx.tar.gz.asc
curl -fsS https://nginx.org/keys/pluknet.key -o source.key
gpg --show-keys --with-colons source.key | grep -q D6786CE303D9A9022998DC6CC8464D549AF75C0A
gpg --import source.key
gpg --verify nginx.tar.gz.asc nginx.tar.gz
sha256sum nginx.tar.gz > /out/nginx-source.sha256
tar -xzf nginx.tar.gz
commit=$(python3 -c 'import json; print(json.load(open("/repo/rtmp-sources.json"))["nginx-rtmp-module"]["commit"])')
git init nginx-rtmp-module
git -C nginx-rtmp-module fetch --depth=1 https://github.com/arut/nginx-rtmp-module.git "$commit"
git -C nginx-rtmp-module checkout --detach FETCH_HEAD
[[ $(git -C nginx-rtmp-module rev-parse HEAD) == "$commit" ]]
export SOURCE_DATE_EPOCH=$(git -C nginx-rtmp-module show -s --format=%ct HEAD)
git -C nginx-rtmp-module archive HEAD | sha256sum > /out/rtmp-source.sha256
cd /work/nginx-1.31.6
python3 - <<'PY'
import shlex,subprocess
args=shlex.split(subprocess.check_output(['nginx','-V'],stderr=subprocess.STDOUT).decode().split('configure arguments: ',1)[1])
subprocess.run(['./configure',*args,'--add-dynamic-module=/work/nginx-rtmp-module'],check=True)
PY
make -j"$(nproc)" modules
python3 /repo/scripts/package_rtmp.py
apt-get install -y --no-install-recommends /out/*.deb
python3 /repo/tests/rtmp-live.py > /out/rtmp-live.txt 2>&1
(cd /out && sha256sum *.deb > SHA256SUMS)

tar -czf /out/iptv-nginx-config.tar.gz -C /repo/config iptv
