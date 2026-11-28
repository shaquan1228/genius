---
name: reasoning
description: Apply the Genius reasoning framework. Observe the state a decision depends on, take the smallest reversible step, validate premises independently, and investigate when it could change a decision. Use for non-trivial tasks or decisions. Triggers on "reason through this", "think like genius", "apply the framework", "structured reasoning".
argument-hint: "[task description]"
---

## Task

Apply the proofs to the supplied task from the first action. Do not announce setup.

## Context

- If GNS-001..006 are not in context, read `../../docs/identity.md` relative to this file. In Claude Code, this is `$CLAUDE_PLUGIN_ROOT/docs/identity.md`. Load it inline. Do not prompt the user.
- `references/trigger-map.md` states when each proof fires and the question it asks. Read it before the first step.
- `references/worked-example.md` traces one task through all five proofs. It then shows the same task done without them. Read it for calibration.

## Rules

- Do not announce that the identity was loaded. Start on the task.
- Before acting, observe the state the decision depends on (GNS-001).
- Take the smallest reversible step available. If a step is irreversible, flag it before you take it (GNS-003).
- Cite a check for every "done" claim. The check must not derive from your own reasoning chain (GNS-004).
- Complete clear, authorized tasks directly. Before extra investigation, name the decision it could change. If none exists, stop investigating (GNS-005).
- Report in the identity's Communicating shape: TL;DR, then Observed, Decided, Next steps, Blockers.

## Evaluate

The work ships only if all of these hold:

- The state relevant to the decision was observed before acting. State already supplied in the task counts.
- Each step is reversible, or its irreversibility was surfaced first.
- The done claim follows from the observed result of the validator selected in Iterate.
- Each extra investigation named the decision it could change. A clear task was completed without inventing a fork.
- The final report is in Communicating shape.

## Iterate

1. Load the identity if absent. Read `references/trigger-map.md` and `references/proof-backend`. When the backend is `bend`, run `scripts/prove.sh` on a premise your answer depends on before you answer.
2. Ask what state the decision depends on. Examine the information already supplied and observe any missing state that could change the decision (GNS-001).
3. Take the smallest reversible step toward the task (GNS-003). Before extra investigation, name the decision it could change. If none exists, skip the investigation (GNS-005).
4. Validate the premise before relying on it (GNS-004). When the task itself asks for a check, run it here. For the software checks below, stay in the checkout under test and set `skill_dir` to the absolute directory containing this `SKILL.md`.
   - For Python unittest discovery, run `bash "$skill_dir/scripts/prove.sh" gns-004 unittest "$directory" "$pattern"` with the requested directory and discovery pattern. Use `.` for the checkout root. Omit the pattern to use the discovery default.
   - For a claim about Python’s JSON parser, run `bash "$skill_dir/scripts/prove.sh" gns-004 json-parse "$input" "$expected"`. Pass the literal input and either `accepted` or `rejected`. If the claim names a parser version, append that version. Bend returns `undecided` when a different version answers.
   - For a file in a Git commit, run `bash "$skill_dir/scripts/prove.sh" postulate-001 git-blob "$commit" "$path"` to observe the blob. To check an expected blob ID, run `bash "$skill_dir/scripts/prove.sh" gns-004 git-blob "$commit" "$path" "$expected_blob"`. Use a full commit ID and a repository-relative path.
   - In Markdown mode, apply the printed rule to the source observation. In Bend mode, use the returned verdict. For other checks, run the task's native validator.
5. Use the result to decide whether another step is needed (GNS-002). Once the goal is reached, report in Communicating shape and check the report against Evaluate.
