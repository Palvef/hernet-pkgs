#!/bin/bash
# apt-ftparchive scans existing Release files too: remove the prior file from
# its input tree before regeneration so the new document cannot hash the old one.
set -euo pipefail
cd "${1:?repository root}"
suite=${2:?suite}
dist="dists/$suite"
release_tmp=$(mktemp -d)
cleanup() {
 if [[ -f "$release_tmp/Release" && ! -f "$dist/Release" ]]; then
  mv "$release_tmp/Release" "$dist/Release"
 fi
 rm -rf "$release_tmp"
}
trap cleanup EXIT
if [[ -f "$dist/Release" ]]; then mv "$dist/Release" "$release_tmp/Release"; fi
apt-ftparchive -o APT::FTPArchive::Release::Origin=HerNet -o APT::FTPArchive::Release::Label=HerNet -o APT::FTPArchive::Release::Suite="$suite" -o APT::FTPArchive::Release::Codename="$suite" -o APT::FTPArchive::Release::Architectures=amd64 -o APT::FTPArchive::Release::Components=main release "$dist" > "$dist/Release.new"
mv "$dist/Release.new" "$dist/Release"
