# Examples

Excerpts from contracts that held through a session — the one line worth copying or fixing, never a whole contract.

## Keep doing

- **Branch field echoes an observed branch, not a wished one.**
  > Target branch: `fix/retry-payment-client` (observed via `git branch --show-current`). Not stacked. — GNS-003

  The command output is the proof. Without it the field is a guess.

- **In-scope names files that were read or grepped.**
  > In scope: `lib/payments/client.rb:41-88` (read), `spec/payments/client_spec.rb` (read). — GNS-001

  A line range means the file was opened. A bare path might be assumed.

- **Off-limits names the specific temptation, not a category.**
  > Off-limits: the deprecated `retry_with_backoff` helper two files over. Do not delete it in this PR. — GNS-005

  A concrete "while I'm here" is what stops the drift. "No refactors" is too vague to bite.

- **Output shape is one noun.**
  > Output: diff plus 5-bullet summary. — GNS-002

  Naming the shape is how iteration knows to stop.

- **Gate names the command and the passing signal.**
  > Gate: `bundle exec rspec spec/payments/client_spec.rb` green; `git diff --stat` touches only in-scope files. — GNS-004

  A gate without a passing signal is a suggestion.

## Traps (rewrite before binding)

- **Guessed branch.**
  > Target branch: probably `main`.

  "Probably" means unobserved. → Run the branch command. Echo the output.

- **Assumed file.**
  > In scope: the payment client, wherever it lives.

  → Grep for it. List the path that came back. If nothing came back, observation has not happened yet.

- **Tool named where an outcome belongs.**
  > Gate: `gt submit` succeeds.

  Assumes Graphite is authenticated here. → "Open the PR with whatever branch tooling is present; gate is specs green and diff-stat matches scope."

- **Scope drift mid-task, patched in place.**
  > Updated in-scope to also include the config loader.

  Editing a field silently is how scope expands. → Return to step 3. Bind a fresh contract and say why.

## One rejected-then-fixed contract

**Rejected** — three fields fail Evaluate:

```
## Preflight Contract
- Branch: main (assumed)                              — GNS-003
- In scope: payment client and its tests             — GNS-001
- Off-limits: no refactors                           — GNS-005
- Output: diff                                       — GNS-002
- Gate: srb tc and packwerk pass                     — GNS-004
```

Branch is assumed. In-scope has no paths. Gate names tools not yet observed in this repo.

**Fixed** — every line carries an observation:

```
## Preflight Contract
- Branch: fix/retry-payment-client (git branch --show-current); not stacked   — GNS-003
- In scope: lib/payments/client.rb:41-88, spec/payments/client_spec.rb (read)  — GNS-001
- Off-limits: deprecated retry_with_backoff helper; config loader              — GNS-005
- Output: diff + 5-bullet summary                                              — GNS-002
- Gate: bundle exec rspec spec/payments/client_spec.rb green (runner observed
  in Gemfile); git diff --stat touches only in-scope files                    — GNS-004
```
