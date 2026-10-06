#!/bin/bash
set -euo pipefail
repo_root=$(realpath "$(dirname "$0")/..")
artifacts=$(realpath "${1:?artifacts}")
site=$(realpath "${2:?site}")
: "${APT_SIGNING_KEY:?Set Actions secret APT_SIGNING_KEY to ASCII-armored private key}"
: "${APT_SIGNING_FINGERPRINT:?Set repository variable APT_SIGNING_FINGERPRINT}"
export GNUPGHOME=$(mktemp -d)
chmod 700 "$GNUPGHOME"
trap 'rm -rf "$GNUPGHOME"' EXIT
printf '%s' "$APT_SIGNING_KEY" | gpg --batch --import
unset APT_SIGNING_KEY
gpg --batch --list-secret-keys "$APT_SIGNING_FINGERPRINT" >/dev/null
mkdir -p "$site/pool" "$site/dists"
python3 scripts/archive.py "$artifacts" "$site"
cp docs/index.html "$site/index.html"
cp docs/lua-dependencies.txt "$site/lua-dependencies.txt"
python3 - "$site" <<'PYINDEX'
import pathlib,sys
root=pathlib.Path(sys.argv[1])
with (root/'lua-dependencies.txt').open('a') as out:
 out.write('\n# Available signed Lua, NDK and library dependency packages:\n')
 for p in sorted(p for pattern in ['nginx-lua-libraries-ha_*.deb','nginx-module-ndk-ha_*.deb','nginx-module-lua-ha_*.deb'] for p in root.rglob(pattern)):
  out.write('https://hernet-pkgs.palve.moe/'+p.relative_to(root).as_posix()+'\n')
PYINDEX
printf 'hernet-pkgs.palve.moe\n' > "$site/CNAME"
touch "$site/.nojekyll"
gpg --batch --armor --export "$APT_SIGNING_FINGERPRINT" > "$site/hernet-pkgs.asc"
gpg --batch --export "$APT_SIGNING_FINGERPRINT" > "$site/hernet-pkgs.gpg"
cd "$site"
for suite in bookworm trixie jammy noble resolute; do
 mkdir -p "dists/$suite/main/binary-amd64"
 : > "dists/$suite/main/binary-amd64/Packages"
 for directory in pool/*/"$suite"; do
  [[ -d "$directory" ]] || continue
  apt-ftparchive packages "$directory" >> "dists/$suite/main/binary-amd64/Packages"
 done
 gzip -n -9 -c "dists/$suite/main/binary-amd64/Packages" > "dists/$suite/main/binary-amd64/Packages.gz"
 bash "$repo_root/scripts/release.sh" "$site" "$suite"
 printf '%s' "${APT_SIGNING_PASSPHRASE:-}" | gpg --batch --yes --pinentry-mode loopback --passphrase-fd 0 --local-user "$APT_SIGNING_FINGERPRINT" --clearsign --output "dists/$suite/InRelease" "dists/$suite/Release"
 printf '%s' "${APT_SIGNING_PASSPHRASE:-}" | gpg --batch --yes --pinentry-mode loopback --passphrase-fd 0 --local-user "$APT_SIGNING_FINGERPRINT" --armor --detach-sign --output "dists/$suite/Release.gpg" "dists/$suite/Release"
 gpg --verify "dists/$suite/InRelease"
 gpg --verify "dists/$suite/Release.gpg" "dists/$suite/Release"
done
