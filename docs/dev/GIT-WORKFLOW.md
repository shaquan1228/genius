# Git Workflow

Git operations, commit guidelines, worktrees, and stack management.

## Tools

- [graphite][graphite-cli-docs]
- [git][git-cli-docs]
- [scripts in `bin/` related to worktrees][quanbot-bin]

## Rules

- [**Always check your environment before issuing commands**][qbt-001]
- When making commits, [_always observe your commit context first_][qbt-001]. Prefer amend. New commit only when crossing a logical boundary.
- Commit early, commit often. We can always amend the correct commit layer.
- When creating worktrees, always use `bin/worktree`, not `git worktree`
- Never run `gt repo sync` within worktrees.
- Remain in worktrees until told to leave
- Use descriptive commit messages

---

[graphite-cli-docs]: https://graphite.com/docs/command-reference "graphite cli reference"
[git-cli-docs]: https://git-scm.com/docs/git#_git_commands "git cli reference"
[quanbot-bin]: ../../bin/ "quanbot bin scripts folder"
[qbt-001]: ../proofs/001-OBSERVATION-PRECEDENCE.md "bbservation precedence proof"
