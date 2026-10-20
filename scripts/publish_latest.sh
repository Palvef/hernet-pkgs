#!/bin/bash
set -euo pipefail
repo_root=$(realpath "$(dirname "$0")/..")
artifacts=$(realpath "${1:?artifacts}")
site=$(realpath "${2:?site}")
: "${APT_SIGNING_KEY:?Signing key required}"
: "${APT_SIGNING_FINGERPRINT:?Signing fingerprint required}"
export GNUPGHOME=$(mktemp -d)
chmod 700 "$GNUPGHOME"
trap 'rm -rf "$GNUPGHOME"' EXIT
printf '%s' "$APT_SIGNING_KEY" | gpg --batch --import
unset APT_SIGNING_KEY
python3 "$repo_root/scripts/archive_latest.py" "$artifacts" "$site"
gpg --batch --armor --export "$APT_SIGNING_FINGERPRINT" > "$site/hernet-pkgs.asc"
gpg --batch --export "$APT_SIGNING_FINGERPRINT" > "$site/hernet-pkgs.gpg"
printf 'hernet-pkgs.palve.moe\n' > "$site/CNAME"
touch "$site/.nojekyll"
for distro in debian ubuntu; do
 root="$site/mainline/$distro"
 mkdir -p "$root/pool" "$root/dists"
 suites='bookworm trixie'
 if [[ $distro == ubuntu ]]; then suites='jammy noble resolute'; fi
 for suite in $suites; do
  mkdir -p "$root/dists/$suite/main/binary-amd64"
  (cd "$root"; for directory in pool/*/"$suite"; do
   [[ -d "$directory" ]] || continue
   apt-ftparchive packages "$directory"
  done) > "$root/dists/$suite/main/binary-amd64/Packages"
  gzip -n -9 -c "$root/dists/$suite/main/binary-amd64/Packages" > "$root/dists/$suite/main/binary-amd64/Packages.gz"
  bash "$repo_root/scripts/release.sh" "$root" "$suite"
  printf '%s' "${APT_SIGNING_PASSPHRASE:-}" | gpg --batch --yes --pinentry-mode loopback --passphrase-fd 0 --local-user "$APT_SIGNING_FINGERPRINT" --clearsign --output "$root/dists/$suite/InRelease" "$root/dists/$suite/Release"
  printf '%s' "${APT_SIGNING_PASSPHRASE:-}" | gpg --batch --yes --pinentry-mode loopback --passphrase-fd 0 --local-user "$APT_SIGNING_FINGERPRINT" --armor --detach-sign --output "$root/dists/$suite/Release.gpg" "$root/dists/$suite/Release"
  gpg --verify "$root/dists/$suite/InRelease"
 done
done
cp "$repo_root/docs/iptv-rtmp.md" "$site/iptv-rtmp.md"
python3 "$repo_root/scripts/index_latest.py" "$site"
