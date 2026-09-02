# Examples

Excerpts from contracts that held through a session. Each shows the one line to copy or fix. None is a whole contract.

## Keep doing

- **Branch field echoes an observed branch, not a wished one.**
  > Target branch: `fix/retry-payment-client` (observed via `git branch --show-current`). Not stacked. (GNS-003)

  The command output is the proof. Without it, the field is a guess.

- **In-scope names files that were read or grepped.**
  > In scope: `lib/payments/client.rb:41-88` (read), `spec/payments/client_spec.rb` (read). (GNS-001)

  A line range means the file was opened. A bare path can be an assumption.

- **Off-limits names the specific temptation, not a category.**
  > Off-limits: the deprecated `retry_with_backoff` helper two files over. Do not delete it in this PR. (GNS-005)

  A concrete "while I'm here" stops the drift. "No refactors" is too vague to bite.

- **Output shape is one noun.**
  > Output: diff plus 5-bullet summary. (GNS-002)

  The named shape tells iteration when to stop.

- **Gate names the command and the passing signal.**
  > Gate: `bundle exec rspec spec/payments/client_spec.rb` green; `git diff --stat` touches only in-scope files. (GNS-004)

  A gate without a passing signal is a suggestion.

## Traps (rewrite before binding)

- **Guessed branch.**
  > Target branch: probably `main`.

  "Probably" means unobserved. Rewrite: run the branch command. Echo the output.

- **Assumed file.**
  > In scope: the payment client, wherever it lives.

  Rewrite: grep for it. List the path that came back. If nothing came back, observation has not happened yet.

- **Tool named where an outcome belongs.**
  > Gate: `gt submit` succeeds.

  This assumes Graphite is authenticated here. Rewrite: "Open the PR with the branch tooling present. The gate is specs green and diff-stat matches scope."

- **Test runner carried over from the last repo.**
  > Gate: `bundle exec rspec` green.

  This repo has no Gemfile. It has a `Makefile` with a `tests` target and doctest. Rewrite: observe the build file first. Name the target you saw: `make tests FILTER=sizing_policy`.

- **Scope drift mid-task, patched in place.**
  > Updated in-scope to also include the config loader.

  A silent field edit is how scope expands. Rewrite: return to step 3. Bind a fresh contract. Say why.

## One rejected-then-fixed contract

**Rejected.** Three fields fail Evaluate.

```
## Preflight Contract
- Branch: main (assumed)                              (GNS-003)
- In scope: payment client and its tests             (GNS-001)
- Off-limits: no refactors                           (GNS-005)
- Output: diff                                       (GNS-002)
- Gate: srb tc and packwerk pass                     (GNS-004)
```

The branch is assumed. In-scope has no paths. The gate names tools not yet observed in this repo.

**Fixed.** Every line carries an observation.

```
## Preflight Contract
- Branch: fix/retry-payment-client (git branch --show-current); not stacked   (GNS-003)
- In scope: lib/payments/client.rb:41-88, spec/payments/client_spec.rb (read)  (GNS-001)
- Off-limits: deprecated retry_with_backoff helper; config loader              (GNS-005)
- Output: diff + 5-bullet summary                                              (GNS-002)
- Gate: bundle exec rspec spec/payments/client_spec.rb green (runner observed
  in Gemfile); git diff --stat touches only in-scope files                    (GNS-004)
```

## A second fixed contract, C++ repo

Task: "Add a `KellyFraction` sizing policy." The repo is header-only C++ with a hand-written Makefile. Nothing autoloads. The in-scope list must include the umbrella include.

```
## Preflight Contract
- Branch: feat/kelly-sizing (git branch --show-current); no stacking tool present     (GNS-003)
- In scope: src/primitives/sizing_policy/generics/kelly_fraction.hpp (new);
  src/primitives/sizing_policy/sizing_policies.hpp:6-11 (umbrella include, read);
  tests/primitives/sizing_policy/sizing_policies.cpp (read)                          (GNS-001)
- Off-limits: the duplicated BACKOFF constants in composition/events/publisher.cpp
  and consumer.cpp; the TODO in cli/capabilities.hpp:63                              (GNS-005)
- Output: diff + 5-bullet summary                                                    (GNS-002)
- Gate: make tests FILTER=sizing_policy green (target observed in Makefile:72);
  make lint clean (clang-tidy caps function size at 25 lines, .clang-tidy);
  git diff --stat touches only in-scope files                                        (GNS-004)
```

The sibling to copy is `generics/fixed_fraction.hpp:11`. Its constructor validates and throws. Match that pattern. Do not add a new one.
