#!/usr/bin/env bash
# Extract the pinned release into an existing directory.
set -euo pipefail

version=2.0.40
case "$(uname -m)" in
  x86_64)
    arch=x64
    sha256=c9ff8d67bd903fb6ad9a26b43d8a62c01021de82a44d55ce4a3dcd4732113d6b
    ;;
  aarch64|arm64)
    arch=arm64
    sha256=2f42a6fa34ecdaa71ae105e5fa734f9a07e129d333e45448ab6d2ff03a837570
    ;;
  *) echo "Unsupported Linux architecture for Bend: $(uname -m)" >&2; exit 1 ;;
esac

archive=$(mktemp)
trap 'rm -f -- "$archive"' EXIT
url="https://github.com/bendlang/bend/releases/download/v$version/bend-$version-linux-$arch.tar.gz"
curl --proto '=https' --tlsv1.2 --fail --location --silent --show-error \
  "$url" --output "$archive" || { echo "Download failed: $url" >&2; exit 1; }
printf '%s  %s\n' "$sha256" "$archive" | sha256sum --check --status \
  || { echo "SHA-256 verification failed for Bend $version ($arch)" >&2; exit 1; }
tar -xzf "$archive" -C "$1"
