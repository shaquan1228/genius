# Shared by executable entry points; sourcing this file performs no work.
# Bash 3.2 is the minimum supported shell (the macOS system version).
CLI_TEMP_PATHS=('')

cli_init() {
  trap cli_cleanup EXIT
  trap 'cli_interrupt 129' HUP
  trap 'cli_interrupt 130' INT
  trap 'cli_interrupt 143' TERM
}

cli_cleanup() {
  local status=$? path
  for path in "${CLI_TEMP_PATHS[@]}"; do
    if [[ -n $path ]]; then rm -rf -- "$path" || :; fi
  done
  return "$status"
}

cli_interrupt() {
  printf '%s: interrupted; cleaning temporary files\n' "${0##*/}" >&2
  exit "$1"
}

cli_help() {
  local arg
  for arg in "$@"; do
    case $arg in -h | --help)
      usage
      exit 0
      ;;
    esac
  done
}

cli_error() { printf '%s: %s\n' "${0##*/}" "$*" >&2; }
cli_die() {
  cli_error "$@"
  exit 1
}
cli_usage_error() {
  cli_error "$@"
  cli_error 'Try --help for usage.'
  exit 2
}

cli_info() {
  printf '%s\n' "$*" >&2
}

cli_no_arguments() {
  if [[ ${1-} == -- ]]; then shift; fi
  if (($#)); then cli_usage_error "Unexpected argument: $1"; fi
}

cli_require() {
  local command
  for command in "$@"; do
    command -v "$command" >/dev/null 2>&1 || cli_die "Missing command: $command. Install it and retry."
  done
}

# Results use REPLY, avoiding command substitutions that lose cleanup registration.
cli_temp_dir() {
  REPLY=$(mktemp -d "${1:-${TMPDIR:-/tmp}}/genius.XXXXXXXX") || return
  CLI_TEMP_PATHS+=("$REPLY")
}

cli_temp_file() {
  REPLY=$(mktemp "$1/.genius.XXXXXXXX") || return
  CLI_TEMP_PATHS+=("$REPLY")
}

file_check() {
  [[ ! -L $1 ]] || cli_die "Refusing to replace symbolic link: $1"
  [[ ! -e $1 || -f $1 ]] || cli_die "Expected a regular file: $1"
}

# Commit only successful producers, using a same-directory rename and existing mode.
file_update() {
  local destination=$1 temporary status
  shift
  file_check "$destination"
  cli_temp_file "$(dirname -- "$destination")" || return
  temporary=$REPLY
  if [[ -f $destination ]]; then cp -p -- "$destination" "$temporary" || return; fi
  if "$@" >"$temporary"; then
    if [[ -f $destination ]] && cmp -s -- "$temporary" "$destination"; then return 0; fi
    mv -f -- "$temporary" "$destination"
  else
    status=$?
    return "$status"
  fi
}
