# Git Workflow

Git operations, commit guidelines, worktrees, and stack management.

## Tools

- [graphite][graphite-cli-docs]
- [git][git-cli-docs]
- [scripts in `bin/` related to worktrees][quanbot-bin]

## Rules

- [**Always check your environment before issuing commands**][qbt-001]
- When making commits, [_always observe your commit context first_][qbt-001]. [_Amend stays in the dwell; a new commit marks a fork — make a new commit only when crossing a logical boundary_][qbt-005].
- [_Commit early, commit often_][qbt-005] — frequent amends load the spring, the fork commit releases it.
- When creating worktrees, always use `bin/worktree`, not `git worktree`
- Never run `gt repo sync` within worktrees.
- Remain in worktrees until told to leave
- Use descriptive commit messages

---

[graphite-cli-docs]: https://graphite.com/docs/command-reference "graphite cli reference"
[git-cli-docs]: https://git-scm.com/docs/git#_git_commands "git cli reference"
[quanbot-bin]: ../../bin/ "quanbot bin scripts folder"
[qbt-001]: ../proofs/001-OBSERVATION-PRECEDENCE.md "observation precedence proof"
[qbt-005]: ../proofs/005-FORK-LOADED-ITERATION.md "fork-loaded iteration proof"
