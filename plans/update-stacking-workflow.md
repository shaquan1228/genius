# Plan: Update quanbot with stacking workflow

## Context

During the billing `Billing::Customer` migration stack (5 PRs), a repeatable pattern emerged
for creating and managing Graphite stacks. The quanbot prompt framework needs to encode this
so future agents follow the same workflow automatically — idempotent branch creation, `gt`
registration, and no-push-by-default discipline.

---

## Files to change

- `/Users/shaquan1228/Desktop/quanbot/rules.md`
- `/Users/shaquan1228/Desktop/quanbot/workflow.md`

---

## Change 1: `rules.md` — expand Source Control Workflow

Replace the existing `## Source Control Workflow` section with:

````markdown
## Source Control Workflow

- Prefer iterative delivery: keep branches and pull requests small, coherent, and sequential.
- Use a stack-aware workflow and keep ancestry healthy before publishing.
- Treat quality gates as required and stage only task-relevant files.
- Never push to remote unless explicitly instructed.

### Stack initialization

When the user asks to "begin working on a stack" (or equivalent), follow this protocol:

1. **Enumerate first.** List all branches in the stack before creating any. Confirm the
   order and parent relationships with the user if unclear.
2. **Create branches idempotently.** For each branch, check out if it already exists,
   otherwise create it:
   ```bash
   git checkout <branch> 2>/dev/null || git checkout -b <branch>
   ```
````

3. **Register with Graphite.** After each branch is checked out, register it:
   ```bash
   gt track --parent <parent-branch>
   ```
4. **Stay on the leaf branch.** After initializing the full stack, remain on the last
   (deepest) branch and begin work there unless the user specifies otherwise.
5. **No push until done.** Do not push any branch until the user explicitly asks to publish.

````

---

## Change 2: `workflow.md` — add Stack Initialization step and update Publish

Insert a new `## 5) Stack Initialization (when starting stacked work)` section before the
existing step 5, then renumber: old step 5 → step 6, old step 6 → step 7.

New step 5:

```markdown
## 5) Stack Initialization (when starting stacked work)

When beginning a stacked PR workflow:

1. Enumerate all planned branches and their parent order before creating any.
2. Create each branch idempotently:
   ```bash
   git checkout <branch> 2>/dev/null || git checkout -b <branch>
````

3. Register each branch with Graphite:
   ```bash
   gt track --parent <parent-branch>
   ```
4. Remain on the leaf branch. Do not push until explicitly instructed.

````

Updated step 6 (was step 5 "Publish") — add the no-push rule:

```markdown
## 6) Publish

- Verify branch scope is single-purpose and reviewable.
- Verify branch stack or ancestry is healthy before publish.
- Confirm required quality gates pass before publish.
- Confirm staged files are only task-relevant.
- Push only when explicitly instructed — never push by default.
````

Updated step 7 (was step 6 "Review Output") — header number only, content unchanged.

---

## Verification

1. Read both files after editing to confirm the changes are present.
2. Check that `rules.md` contains the `### Stack initialization` subsection with the
   idempotent checkout pattern and `gt track` step.
3. Check that `workflow.md` step 5 is "Stack Initialization" and step 6 is "Publish".
4. Confirm no-push rule appears in both files.

---

## Critical files

- `/Users/shaquan1228/Desktop/quanbot/rules.md`
- `/Users/shaquan1228/Desktop/quanbot/workflow.md`
