#!/usr/bin/env bash
# Install Bend into the directory supplied by the caller.
set -euo pipefail

die() {
  echo "$*" >&2
  exit 1
}

if [[ $# != 1 || ! -d $1 ]]; then
  die "Usage: install-bend.sh EXISTING_DIRECTORY"
fi

destination=$1
version=2.0.40
machine=$(uname -m)

case "$machine" in
  x86_64)
    arch=x64
    sha256=c9ff8d67bd903fb6ad9a26b43d8a62c01021de82a44d55ce4a3dcd4732113d6b
    ;;
  aarch64 | arm64)
    arch=arm64
    sha256=2f42a6fa34ecdaa71ae105e5fa734f9a07e129d333e45448ab6d2ff03a837570
    ;;
  *)
    die "Unsupported Linux architecture for Bend: $machine"
    ;;
esac

asset="bend-$version-linux-$arch.tar.gz"
url="https://github.com/bendlang/bend/releases/download/v$version/$asset"
archive=$(mktemp)
trap 'rm -f -- "$archive"' EXIT

if ! curl --proto '=https' --tlsv1.2 --fail --location --silent --show-error \
    --output "$archive" "$url"; then
  die "Download failed: $url"
fi

if ! printf '%s  %s\n' "$sha256" "$archive" | sha256sum --check --status; then
  die "SHA-256 verification failed: $asset"
fi

tar -xzf "$archive" -C "$destination"
