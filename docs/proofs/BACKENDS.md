# Markdown and Bend reasoning

Genius has two explicit treatments of the same postulate/proof corpus:

- **Markdown**: read the written discrete-math argument and its interpretation. This remains the default.
- **Bend**: load the corresponding Bend 2 proof after checking it with the Lean-backed kernel. The premises, intermediate implications, and conclusions are represented as types and proof functions.

This is a proof-source seam. It does not replace the agent's reasoning loop with a runtime classifier.

## Choose from the reasoning skill

```text
/genius:reasoning <task> backend:markdown
/genius:reasoning <task> backend:bend
```

In Codex, invoke the same skill as `$genius:reasoning` with the task and backend selection. The skill keeps the identity and behavioral rules in both modes. Bend mode runs the proof command and loads the checked formal treatment. A missing compiler, missing kernel, or failed check stops that selection with an error; it never silently falls back to Markdown.

The standalone command must be available from the full plugin checkout. Evaluation instruction-only snapshots currently bundle `docs/` and `skills/`, not `bin/` or the Bend toolchain; enabling Bend inside those snapshots needs that explicit packaging work rather than assuming the command is present.

## Choose from the command

From the repository or plugin root:

```sh
python3 bin/genius-proof --list
python3 bin/genius-proof GNS-004 --backend markdown
python3 bin/genius-proof GNS-004 --backend bend
python3 bin/genius-proof all --backend bend --check-only
```

`POSTULATE-001` selects the open postulate. `GNS-001` through `GNS-006` select individual proofs. With no ID, the command selects the entire corpus. Markdown mode prints the `.md` source without invoking a compiler. Bend mode checks the `.bend` source before printing it. `--check-only` omits source text, not verification.

Requirements for the default Bend mode are Bend 2 and Lean v4.34.0 on `PATH`, or a built kernel configured through Bend's `BENDTT` environment variable. This corpus was verified with Bend 2.0.40 and Lean v4.34.0. A custom compiler path can be selected using `--bend /absolute/path/to/bend` or `BEND_BIN`.

An explicitly weaker check is available for learning when the kernel is unavailable:

```sh
python3 bin/genius-proof GNS-004 --backend bend --ordinary
```

This runs Bend's ordinary checker and labels its result accordingly. The reasoning skill may use it only when requested explicitly. No command installs a compiler, changes harness settings, or publishes anything.

## One formal file per source

| ID | Written source | Formal source |
| --- | --- | --- |
| POSTULATE-001 | [The Loop Is Epistemology](../postulates/001-THE-LOOP-IS-EPISTEMOLOGY.md) | [POSTULATE-001](../postulates/POSTULATE-001-THE-LOOP-IS-EPISTEMOLOGY.bend) |
| GNS-001 | [Observation Precedence](001-OBSERVATION-PRECEDENCE.md) | [GNS-001](GNS-001-OBSERVATION-PRECEDENCE.bend) |
| GNS-002 | [Iterative Refinement](002-ITERATIVE-REFINEMENT.md) | [GNS-002](GNS-002-ITERATIVE-REFINEMENT.bend) |
| GNS-003 | [Smallest Reversible Action](003-SMALLEST-REVERSIBLE-ACTION.md) | [GNS-003](GNS-003-SMALLEST-REVERSIBLE-ACTION.bend) |
| GNS-004 | [Independent Premise Validation](004-INDEPENDENT-PREMISE-VALIDATION.md) | [GNS-004](GNS-004-INDEPENDENT-PREMISE-VALIDATION.bend) |
| GNS-005 | [Fork-Loaded Iteration](005-FORK-LOADED-ITERATION.md) | [GNS-005](GNS-005-FORK-LOADED-ITERATION.bend) |
| GNS-006 | [Structural Enforcement](006-STRUCTURAL-ENFORCEMENT-CROSS-LOOP.md) | [GNS-006](GNS-006-STRUCTURAL-ENFORCEMENT-CROSS-LOOP.bend) |

The formal filenames start with the ID prefix because Bend 2.0.40 cannot import a module whose filename starts with a digit. Each file can be checked independently; the common [logic module](logic.bend) defines conjunction, disjunction, equivalence, exclusive alternatives, and explicit reductio.

## Proof coverage and assumptions

- **Postulate 001** remains an open hypothesis. Its file declares the hypothesis and derives conditional consequences, including that derivation without a loop witness does not establish knowledge. The other six files do not import the postulate as a foundation.
- **GNS-001** composes P1–P3 to prove observation precedence.
- **GNS-002** preserves the unfinished-goal trigger and P1–P3. The imported parent premise is not confused with the parent's different theorem conclusion.
- **GNS-003** preserves the active-loop and unfinished-goal trigger and derives both minimality and reversibility.
- **GNS-004** exposes the normative no-cascade-risk premise, derives the contradiction burden constructively, and supplies the written proof's classical reductio explicitly to reach its conclusion.
- **GNS-005** proves both directions of the equivalence and corollary 005.1. Classical contraposition is explicit. P2's exclusive alternatives support the corollary; the operational “name a fork” heuristic is not promoted into a logical theorem.
- **GNS-006** preserves separate state-0/state-1 propositions, all P1–P6, the full P6 conjunction, both directions of the equivalence, and the trusted-agent corollary. Background conclusions from P1/GNS-004 are distinguished from premises actually used by the two conditional directions.

The proposition types are schemas for an arbitrary fixed action, premise, or loop instance. They are not boolean evidence flags. A witness is a proof term, and an implication is a function from witnesses to witnesses. Where mathematical derivations reuse a positive witness, Bend's `Data` kind and `+` quantity make that reuse explicit; logical function hypotheses remain affine.

The supplied hypotheses remain hypotheses. The kernel checks that the conclusion follows from them; it does not certify their normative justification or empirical truth. The formal and written sources require joint review when either argument changes—there is no automatic natural-language equivalence checker. Bend's parser, translation into the kernel, and execution backend retain their documented trust boundaries.

## Verify the seam and the corpus

```sh
python3 -m unittest discover -s tests -p test_proof_backend.py -v
```

With `BEND_BIN` set (or `bend` on `PATH`), these tests also check all seven real files with `--verdict` and reject invalid derivations using exact type-mismatch diagnostics. Without Bend they report those compiler-dependent cases as skipped. The remaining tests check backend selection, missing tools/files, version rejection, explicit ordinary-checker use, and absence of Markdown fallback. Their fake compiler tests exercise only adapter behavior; they are not evidence that a mathematical proof passes.
