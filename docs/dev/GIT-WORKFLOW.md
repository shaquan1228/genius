# Git Workflow

Git operations, commit guidelines, worktrees, and stack management.

## Commits: When to Amend vs New Commit

### AMEND when:

- Fixing typo/linting in feature branch (not yet PR'd)
- Correcting test that was part of same logical change
- Updating docs for feature in same commit
- Agent made error in previous commit (< 5 min ago)
- User explicitly says "amend" or "fix that commit"

### NEW COMMIT when:

- Feature is working, now refactoring/optimizing
- Adding tests for existing feature (checkpoint)
- PR already exists (never amend pushed commits)
- Crossing logical boundary (setup → implementation)
- User explicitly says "checkpoint" or "save this"
- More than 5 minutes since last commit
- Different logical unit of work

### Commands:

```bash
# Amend without editing message
git commit --amend --no-edit

# Amend and edit message
git commit --amend

# New commit with type prefix
git commit -m "feat: description"
git commit -m "fix: description"
git commit -m "checkpoint: description"
```

### Decision Tree:

```
Need to commit changes?
  ↓
Is this fixing the previous commit?
  ↓ YES → git commit --amend --no-edit
  ↓ NO
Is this a checkpoint (working state)?
  ↓ YES → git commit -m "checkpoint: <description>"
  ↓ NO
Is this completing a feature unit?
  ↓ YES → git commit -m "feat: <description>"
```

---

## Worktrees: Temporal vs Permanent

### TEMPORAL worktrees (auto-cleanup after 7 days):

**Naming patterns:**

- `temp-<sanitized>-<timestamp>` - Created by `worktree --temporal`
- `temp-fix-<issue>` - Quick fixes

**When to use:**

- Agent tasks assigned by user
- Experiments or proof-of-concepts
- Quick fixes that will be merged soon
- Parallel work that's short-lived

**Creation:**

```bash
# Auto-named, tracked with graphite
worktree --temporal --with-graphite "implement user auth"

# Explicit name
worktree --temporal fix-experiment main
```

### PERMANENT worktrees (manual cleanup):

**Naming patterns:**

- `keep-quick-fixes` - Ongoing hotfix work
- `keep-<feature>` - Long-running parallel feature
- Any worktree without `temp-` or `agent-` prefix

**When to use:**

- Long-running feature branches
- Persistent hotfix workspace
- Multiple related features in parallel

**Creation:**

```bash
# Permanent worktree
worktree keep-quick-fixes main

# Regular branch (permanent by default)
worktree feature-user-dashboard main
```

### Decision Tree:

```
Starting new work?
  ↓
Is this temporal? (< 1 week, experiment, agent task)
  ↓ YES → worktree --temporal --with-graphite "<task>"
  ↓ NO
Is this long-running? (> 1 week, persistent)
  ↓ YES → worktree keep-<feature> main
  ↓ NO
Use regular branch in main repo
```

---

## Graphite Sync Protocol

### BEFORE any git operation:

1. Check if in worktree:

   ```bash
   git rev-parse --git-dir | grep worktrees
   ```

2. If in worktree:
   - Use standard git commands
   - DO NOT run `gt sync` (causes branch checkout conflicts)
   - DO NOT run `gt stack submit` from worktree

3. If in main repo:
   - Safe to use all gt commands
   - `gt sync` works normally
   - `gt stack submit` works normally

### Worktree-safe operations:

```bash
# Safe in worktrees
git status
git add
git commit
git push
gt log
gt status

# NOT safe in worktrees (run from main repo)
gt sync
gt stack submit
gt repo sync
```

---

## Stack Initialization

When beginning a stacked PR workflow:

1. **Enumerate first.** List all planned branches and their parent order before creating any.

2. **Create each branch idempotently:**

   ```bash
   git checkout <branch> 2>/dev/null || git checkout -b <branch>
   ```

3. **Register each branch with Graphite:**

   ```bash
   gt track --parent <parent-branch>
   ```

4. **Remain on the leaf branch.** Do not push until explicitly instructed.

---

## Cleanup Protocol

### Temporal worktrees:

- Auto-cleanup eligible after 7 days
- Run manually: `worktree-cleanup`
- Dry-run first: `worktree-cleanup --dry-run`
- Custom age: `worktree-cleanup --age-days=14`

### When agent finishes task:

1. Ensure all changes are committed
2. Push branch if ready for PR
3. Return to main repo
4. Let temporal worktree age out naturally (7 days)
5. Or remove immediately if task is complete and merged

### Manual cleanup:

```bash
# List all worktrees
git worktree list

# Remove specific worktree
git worktree remove ~/Desktop/repo-worktrees/branch-name

# Force remove (if uncommitted changes)
git worktree remove --force ~/Desktop/repo-worktrees/branch-name
```

---

## Best Practices

1. **Commit early, commit often** - Small commits are easier to review
2. **Use descriptive commit messages** - Future you will thank you
3. **Don't amend pushed commits** - Causes problems for collaborators
4. **Clean up temporal worktrees** - Run cleanup weekly
5. **Stay in worktree for task** - Don't switch back to main until done
6. **Check worktree status** - Before running graphite commands
7. **Log everything** - All worktree operations log to ~/.quanbot/worktree.log

---

For the overall development process (TDD, planning, verification), see `docs/dev/WORKFLOW.md`.
