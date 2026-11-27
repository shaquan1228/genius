#!/usr/bin/env bash
set -euo pipefail

readonly LEAN_VERSION=4.34.0
readonly LEAN_SHA256=caaa98356098c85dc0fcbbd28e1ec66f39eb6551829972b752ff20e1286b646b
STAGING_DIR=''

usage() {
  cat <<'HELP'
Usage: .github/scripts/install-proof-toolchain.sh DESTINATION
Install the pinned Bend 2 and Lean releases for Linux x86_64 into a new directory.
Archives are SHA-256 verified before extraction. Existing installations are not replaced.
When GITHUB_PATH and GITHUB_ENV are set, expose the installed tools to later steps.
Otherwise, print the paths for local use; shell startup files are never modified.

Options:
  -h, --help  Show help without downloading or creating files.
HELP
}

die() {
  printf 'install-proof-toolchain: %s\n' "$*" >&2
  exit 1
}

cleanup() {
  local status=$?
  if [[ -n $STAGING_DIR ]]; then rm -rf -- "$STAGING_DIR" || :; fi
  return "$status"
}

download() {
  local url=$1 checksum=$2 archive=$3
  curl --proto '=https' --tlsv1.2 --fail --location --silent --show-error \
    "$url" --output "$archive" || die "Download failed: $url"
  printf '%s  %s\n' "$checksum" "$archive" | sha256sum --check --status \
    || die "SHA-256 verification failed: ${archive##*/}"
}

main() {
  local argument tool destination parent bend_bin lean_bin
  for argument in "$@"; do
    case $argument in -h | --help)
      usage
      return
      ;;
    esac
  done
  if [[ $# != 1 || -z $1 || $1 == -* ]]; then
    usage >&2
    return 2
  fi
  [[ $(uname -s) == Linux && $(uname -m) == x86_64 ]] \
    || die 'This CI installer supports Linux x86_64 only.'
  for tool in curl sha256sum tar zstd; do
    command -v "$tool" >/dev/null 2>&1 || die "Missing required command: $tool"
  done
  if [[ -n ${GITHUB_PATH:-} || -n ${GITHUB_ENV:-} ]]; then
    [[ -n ${GITHUB_PATH:-} && -n ${GITHUB_ENV:-} && -w $GITHUB_PATH && -w $GITHUB_ENV ]] \
      || die 'GITHUB_PATH and GITHUB_ENV must both name writable files.'
  fi
  destination=$1
  [[ $destination != *$'\n'* ]] || die 'Destination must not contain a newline.'
  [[ ! -e $destination && ! -L $destination ]] || die "Destination already exists: $destination"
  parent=$(dirname -- "$destination")
  mkdir -p -- "$parent"
  parent=$(CDPATH='' cd -- "$parent" && pwd -P)
  destination="$parent/$(basename -- "$destination")"
  STAGING_DIR=$(mktemp -d "$parent/.proof-toolchain.XXXXXXXX")
  mkdir "$STAGING_DIR/install"

  bash "$(dirname -- "$0")/../../evals/docker/install-bend.sh" "$STAGING_DIR/install"
  download \
    "https://github.com/leanprover/lean4/releases/download/v$LEAN_VERSION/lean-$LEAN_VERSION-linux.tar.zst" \
    "$LEAN_SHA256" "$STAGING_DIR/lean.tar.zst"
  tar --zstd -xf "$STAGING_DIR/lean.tar.zst" -C "$STAGING_DIR/install"
  [[ -x $STAGING_DIR/install/bend/bin/bend && -x $STAGING_DIR/install/lean-$LEAN_VERSION-linux/bin/lean ]] \
    || die 'Verified archives did not contain the expected executables.'
  mv -nT -- "$STAGING_DIR/install" "$destination"
  [[ ! -d $STAGING_DIR/install ]] || die "Destination already exists: $destination"

  bend_bin="$destination/bend/bin"
  lean_bin="$destination/lean-$LEAN_VERSION-linux/bin"
  if [[ -n ${GITHUB_PATH:-} ]]; then
    printf '%s\n' "$bend_bin" "$lean_bin" >>"$GITHUB_PATH"
    printf 'BEND_BIN=%s/bend\n' "$bend_bin" >>"$GITHUB_ENV"
  fi
  printf 'Bend: %s/bend\nLean: %s/lean\n' "$bend_bin" "$lean_bin"
}

trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
main "$@"
