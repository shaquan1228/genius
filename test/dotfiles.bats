#!/usr/bin/env bats
# Tests for dotfiles — validate exact color values and semantic distinctness

ITERM="$BATS_TEST_DIRNAME/../dotfiles/iterm2-profile.json"
GITCFG="$BATS_TEST_DIRNAME/../dotfiles/gitconfig"

# ── iterm2-profile.json ───────────────────────────────────────────────────────

@test "iterm2-profile.json is valid JSON" {
  jq . "$ITERM" > /dev/null
}

@test "all 16 Ansi colors are defined with RGB values" {
  for i in $(seq 0 15); do
    jq -e ".Profiles[0][\"Ansi ${i} Color\"].\"Red Component\"" "$ITERM" > /dev/null
  done
}

@test "Ansi 15 (bright white/default text) is warm beige — not cold white" {
  # R > B = warm tone; R > 0.90 = not dimmed
  jq -e '.Profiles[0]["Ansi 15 Color"]["Red Component"] > 0.90' "$ITERM" > /dev/null
  jq -e '
    .Profiles[0]["Ansi 15 Color"]["Red Component"] >
    .Profiles[0]["Ansi 15 Color"]["Blue Component"]
  ' "$ITERM" > /dev/null
}

@test "Ansi 9 (error red) is Gruvbox bright red — high R, low G and B" {
  jq -e '.Profiles[0]["Ansi 9 Color"]["Red Component"] > 0.95' "$ITERM" > /dev/null
  jq -e '.Profiles[0]["Ansi 9 Color"]["Green Component"] < 0.25' "$ITERM" > /dev/null
}

@test "Ansi 11 (warning yellow) is Gruvbox bright yellow — high R and G, low B" {
  jq -e '.Profiles[0]["Ansi 11 Color"]["Red Component"] > 0.95' "$ITERM" > /dev/null
  jq -e '.Profiles[0]["Ansi 11 Color"]["Green Component"] > 0.65' "$ITERM" > /dev/null
  jq -e '.Profiles[0]["Ansi 11 Color"]["Blue Component"] < 0.20' "$ITERM" > /dev/null
}

@test "Ansi 9 (red) and Ansi 11 (yellow) are visually distinct — green channel differs by > 0.4" {
  jq -e '
    (.Profiles[0]["Ansi 11 Color"]["Green Component"]
     - .Profiles[0]["Ansi 9 Color"]["Green Component"]) > 0.4
  ' "$ITERM" > /dev/null
}

@test "has at least 4 triggers" {
  count=$(jq '.Profiles[0].Triggers | length' "$ITERM")
  [ "$count" -ge 4 ]
}

@test "every trigger has action, regex, parameter, and enabled" {
  total=$(jq '.Profiles[0].Triggers | length' "$ITERM")
  complete=$(jq '[.Profiles[0].Triggers[] | select(.action and .regex and .parameter and .enabled)] | length' "$ITERM")
  [ "$complete" -eq "$total" ]
}

@test "error trigger uses Gruvbox bright red (#fb4934)" {
  count=$(jq '[.Profiles[0].Triggers[] | select(.parameter | contains("#fb4934"))] | length' "$ITERM")
  [ "$count" -ge 1 ]
}

@test "pass/success trigger uses Gruvbox bright green (#b8bb26)" {
  count=$(jq '[.Profiles[0].Triggers[] | select((.regex | test("pass|success"; "i")) and (.parameter | contains("#b8bb26")))] | length' "$ITERM")
  [ "$count" -ge 1 ]
}

@test "error and pass triggers have different colors" {
  error_color=$(jq -r '[.Profiles[0].Triggers[] | select(.regex | test("error"; "i")) | .parameter] | first' "$ITERM")
  pass_color=$(jq -r '[.Profiles[0].Triggers[] | select(.regex | test("pass|success"; "i")) | .parameter] | first' "$ITERM")
  [ "$error_color" != "$pass_color" ]
}

# ── gitconfig ─────────────────────────────────────────────────────────────────

@test "color.ui is auto" {
  [ "$(git config --file "$GITCFG" color.ui)" = "auto" ]
}

@test "staged files (added) are green" {
  [[ "$(git config --file "$GITCFG" color.status.added)" == *"green"* ]]
}

@test "unstaged files (changed) are yellow" {
  [[ "$(git config --file "$GITCFG" color.status.changed)" == *"yellow"* ]]
}

@test "staged and unstaged use different colors — the original bug" {
  added=$(git config --file "$GITCFG" color.status.added)
  changed=$(git config --file "$GITCFG" color.status.changed)
  [ "$added" != "$changed" ]
}

@test "untracked files use a third color — distinct from staged and unstaged" {
  added=$(git config --file "$GITCFG" color.status.added)
  changed=$(git config --file "$GITCFG" color.status.changed)
  untracked=$(git config --file "$GITCFG" color.status.untracked)
  [ "$untracked" != "$added" ]
  [ "$untracked" != "$changed" ]
}

@test "diff old (deleted) lines are red" {
  [[ "$(git config --file "$GITCFG" color.diff.old)" == *"red"* ]]
}

@test "diff new (added) lines are green" {
  [[ "$(git config --file "$GITCFG" color.diff.new)" == *"green"* ]]
}

@test "diff old and diff new are different colors" {
  old=$(git config --file "$GITCFG" color.diff.old)
  new=$(git config --file "$GITCFG" color.diff.new)
  [ "$old" != "$new" ]
}
