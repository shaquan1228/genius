# Managed identity files; callers initialize the shared CLI helpers first.
IDENTITY_LIB_DIR=$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
readonly IDENTITY_LIB_DIR

identity_preflight() {
  [[ -n ${HOME:-} ]] || cli_die 'HOME is unset. Set it before running this command.'
  cli_require awk cmp cp grep mkdir mktemp mv rm
  file_check "$HOME/.claude/CLAUDE.md"
  file_check "$1/.cursor/rules/genius.mdc"
}

identity_claude() {
  local destination=$1 action=$2 identity=$3
  local input=/dev/null block
  if [[ -f $destination ]]; then input=$destination; fi
  # Preserve an unrelated file byte for byte, including its final newline state.
  if [[ $action == remove ]] && ! grep -Eq '^# (BEGIN|END) GENIUS$' "$input"; then
    return 0
  fi
  block=$(printf '# BEGIN GENIUS\n@%s\n# END GENIUS' "$identity")
  file_update "$destination" env GENIUS_IDENTITY_BLOCK="$block" \
    awk -v action="$action" -f "$IDENTITY_LIB_DIR/managed_block.awk" "$input" \
    || cli_die "Cannot update $destination: check for unmatched or nested GENIUS markers; the file was preserved."
}

identity_cursor() {
  file_update "$1" printf -- \
    '%s\nalwaysApply: true\ndescription: Engineering identity and operating principles\n%s\n\n@%s\n' \
    '---' '---' "$2"
}
