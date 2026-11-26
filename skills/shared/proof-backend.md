# Internal proof loading

All Genius skills use this policy. Proof treatment is an implementation detail, not a skill argument. Keep the identity, behavioral rules, and proof triggers in either treatment.

Resolve the plugin root as `../..` from this file, or `$CLAUDE_PLUGIN_ROOT` in Claude Code. Load `docs/identity.md` inline if needed, without announcing setup. Resolve a proof by its ID using the paired sources in `docs/proofs/BACKENDS.md`; `PROOF-TREE.md` remains the trigger/composability map.

For each needed derivation:

- Prefer the paired Bend file when Bend 2 and its strong kernel are available. Use the installed `bend` executable or an explicitly configured `BEND_BIN`; Lean v4.34.0 on `PATH` or a usable `BENDTT` supplies the kernel. Run `bend <proof.bend> --verdict`, then read the checked file and any imported logical definitions.
- When the formal counterpart or toolchain is unavailable, use the Markdown argument. Do not describe that as machine-checked. No installation or configuration change is required to use a skill.
- If an attempted proof check fails, report it and do not bypass the failure with Markdown. An ordinary `--check-only` result is not a strong-kernel receipt.

Markdown links in skill references identify written sources and operational explanations; they do not replace a formal proof check. Already having the identity or a GNS citation in context does not establish that the current formal source was checked.

Postulate 001 remains an open hypothesis. Bend checks conclusions under named premises; it does not establish those premises' truth, prove facts about the current task, or perform the task's own validation.

For a prompt sent to another agent or session, carry the relevant proof IDs and this loading policy. The recipient resolves the available treatment in its own environment; do not assume your compiler, paths, or check results exist there.
