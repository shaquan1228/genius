#!/usr/bin/env bash
set -eu

usage() {
  cat <<'HELP'
Usage: prove.sh postulate-001 git-blob COMMIT PATH
       prove.sh gns-004 git-blob COMMIT PATH EXPECTED_BLOB
       prove.sh gns-004 unittest DIRECTORY [PATTERN]

Use a full object ID resolving to a commit and a repository-relative path.
A completed lookup tells you whether that path names a blob. An unreadable
commit leaves the question undecided. unittest checks whether the suite passed.
HELP
}

invalid() {
  usage >&2
  exit 2
}

if [[ ${1:-} == --help ]]; then
  usage
  exit 0
fi
[[ $# -ge 2 ]] || invalid

proof=$1
source=$2
shift 2
scripts=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

case "$proof/$source" in
  postulate-001/git-blob|gns-004/git-blob)
    oid='^([0-9a-f]{40}|[0-9a-f]{64})$'
    if [[ $proof == postulate-001 ]]; then
      [[ $# == 2 ]] || invalid
    else
      [[ $# == 3 && $3 =~ $oid ]] || invalid
    fi
    [[ $1 =~ $oid && -n $2 && $2 != /* && $2 != *$'\n'* && $2 != *$'\r'* ]] || invalid
    case "/$2/" in
      */./*|*/../*|*//*) invalid ;;
    esac
    program=check-file.bend
    ;;
  gns-004/unittest)
    [[ $# == 1 || $# == 2 ]] || invalid
    pattern=${2-test*.py}
    [[ -n $1 && -n $pattern ]] || invalid
    set -- "$1" "$pattern"
    program=check-tests.bend
    ;;
  *) invalid ;;
esac

BEND_NO_TELEMETRY=1 exec "${BEND_BIN:-bend}" "$scripts/$program" -- "$@"
