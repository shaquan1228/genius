# Examples

Excerpts from touches. Each one shows the line to copy or the trap to avoid. None of them is a whole session.

## Keep doing

- **Widen rewrites the existing line.**
  > Before: `// Cache keys are user IDs.`
  > After: `// Cache keys are user or org IDs.`
  > Evidence: `key = account.org_id ?? account.user_id` two lines down (read).

  One line changed. The code is byte-identical.

- **Scaffold fixes the deviant, citing the source.**
  > `migrations/0042_add_index.sql`: added the `-- down:` block. Required by `db/README.md` ("every migration declares down") and present in the migration template and the last five migrations (read).

  The template and siblings were not edited. They are the source.

- **Rule lands in the home that a pointer names.**
  > `docs/agents.md` Conventions: `- Format SQL with \`sqlfluff fix\`.` `.cursorrules` only says "Follow docs/agents.md" (read). Three CI jobs run sqlfluff (grepped).

- **A scoped fact stays scoped.**
  > `services/billing/NOTES.md`: `- Amounts are integer cents.` The root guide is untouched. Only `services/billing/` handles amounts (grepped).

- **Report ends with "seen, not touched".**
  > Seen, not touched: "seperate" typo in `docs/setup.md:8`; `old/cache.js` carries the same narrow comment, but nothing imports it.

## Rewrite these

| Trap | Why it fails | Rewrite |
|---|---|---|
| Adds a second bullet that restates an existing rule in new words | The fact now lives twice and will drift | Reword the existing bullet, or make no change and say it already exists |
| Edits `third_party/lib/README` because it has the same gap | Vendored files belong upstream | Leave it. List it under "seen, not touched". |
| Removes a dropped flag from `RELEASE_NOTES.md` | History records what was true then | Remove it only from current docs |
| Puts a one-service convention in the repo-wide guide | It claims scope the evidence does not show | Use that service's doc or section. Run the scope test. |
| Fixes the comment and also renames a variable "while here" | Two intents, and one of them changes behavior | Comment only. List the rename. |
| Picks the template's version when the template and CI disagree | Same-rank conflict decided silently | Report the fork. Do not touch. |
| Rewrites a whole section to "match" | Over budget, and the diff hides the one real change | One hunk. Keep the surrounding lines. |
