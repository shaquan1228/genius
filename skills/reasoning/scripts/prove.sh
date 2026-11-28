#!/usr/bin/env bash
set -eu

usage() {
  cat <<'HELP'
Usage: prove.sh postulate-001 git-blob COMMIT PATH
       prove.sh gns-004 git-blob COMMIT PATH EXPECTED_BLOB
       prove.sh gns-004 poker-to-call STREET_WAGER HERO_COMMITTED EXPECTED
       prove.sh gns-004 unittest DIRECTORY [PATTERN]
       prove.sh gns-004 json-parse INPUT accepted|rejected [PARSER_VERSION]

Use a full object ID resolving to a commit and a repository-relative path.
A completed lookup tells you whether that path names a blob. An unreadable
commit leaves the question undecided. unittest checks whether the suite passed.
json-parse checks the literal input with the installed Python JSON parser.
You can pin the parser version printed by the observer.

poker-to-call checks the amount needed to match the current wager before
stack limits. Use the current street's total wager and the player's total
contribution on that street. Use one unit throughout, with up to two decimal
places.

The markdown backend prints the rule and the source observation for you to
interpret. A completed suite prints its run ID. A successful Git lookup with
no entry means the path has no blob. The bend backend returns a checked verdict. Set GENIUS_PROOF_BACKEND
to markdown or bend to override the skill's proof-backend file.
HELP
}

invalid() {
  usage >&2
  exit 2
}

hundredths() {
  [[ $1 =~ ^([0-9]{1,8})(\.([0-9]{1,2}))?$ ]] || return 1
  local fraction=${BASH_REMATCH[3]:-}00
  printf '%s\n' "$((10#${BASH_REMATCH[1]} * 100 + 10#${fraction:0:2}))"
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
  gns-004/poker-to-call)
    [[ $# == 3 ]] || invalid
    wager=$(hundredths "$1") || invalid
    committed=$(hundredths "$2") || invalid
    expected=$(hundredths "$3") || invalid
    set -- "$wager" "$committed" "$expected"
    program=check-poker-call.bend
    ;;
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
  gns-004/json-parse)
    [[ $# == 2 || ( $# == 3 && -n $3 ) ]] || invalid
    [[ $2 == accepted || $2 == rejected ]] || invalid
    program=check-parser.bend
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

read -r backend < "$scripts/../references/proof-backend"
case "${GENIUS_PROOF_BACKEND-$backend}" in
  bend)
    BEND_NO_TELEMETRY=1 exec "${BEND_BIN:-bend}" "$scripts/$program" -- "$@"
    ;;
  markdown)
    docs="$scripts/../../../docs"
    case "$proof" in
      postulate-001) rule="$docs/postulates/001-THE-LOOP-IS-EPISTEMOLOGY.md" ;;
      gns-004) rule="$docs/proofs/004-INDEPENDENT-PREMISE-VALIDATION.md" ;;
    esac
    cat -- "$rule"
    printf '\nSource observation (%s)\n' "$source"
    case "$source" in
      poker-to-call)
        if (( $2 > $1 )); then
          printf 'The street commitment exceeds the current wager.\n' >&2
          printf 'unavailable\n'
          exit 2
        fi
        printf 'Amount to match (hundredths): %s\n' "$(($1 - $2))"
        ;;
      json-parse)
        printf 'Parser input: %q\n' "$1"
        if [[ $# == 3 ]]; then
          printf 'Requested parser version: %s\n' "$3"
        fi
        printf '%s' "$1" | python3 -I -B "$scripts/observe_json.py"
        ;;
      unittest)
        exec python3 -I -B "$scripts/observe_suite.py" "$@"
        ;;
      git-blob)
        exec git --no-replace-objects --literal-pathspecs ls-tree --full-tree \
          '--format=%(objecttype) %(objectname)' "$1^{commit}" -- "$2"
        ;;
    esac
    ;;
  *)
    echo 'Expected proof backend markdown or bend.' >&2
    exit 2
    ;;
esac
