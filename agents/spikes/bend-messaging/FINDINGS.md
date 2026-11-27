# Spike findings — 2026-11-26

## Purpose

Learn Bend 2 by using it inside Genius. Messaging provides a bounded experiment with data types, reusable quantities, structural recursion, laws, proofs, and JavaScript export. The useful discovery is that Bend can own executable rules while an adapter handles JSON and MCP.

The draft lives under `agents/spikes/bend-messaging/`. It does not replace the existing evaluation kernel or change the Genius identity. Further exploration of executable postulates remains open; this mailbox is one exercise, not the limit of the project.

## Evidence

| Claim | Evidence | Limit |
| --- | --- | --- |
| Bend policy can participate without rewriting the harness | Real `bend policy.bend -o policy.mjs`; Node imports exported `authorize` | JS backend/runtime and foreign conversion are trusted |
| Two separate sessions can discover and message | Real MCP subprocesses sharing SQLite; request/ack/reply integration test | Protocol clients, not two LLM agents |
| Codex can load and call these tools | `codex-smoke.json`, generated from installed Codex app-server and direct `mcpServer/tool/call` | App-server client test, not an independently open TUI or model-driven call |
| Claude notification format is emitted correctly | Channel wire-format integration test | Claude Code unavailable; live delivery untested |
| Cross-project sends and sender overrides are rejected | Real boundary tests execute the generated Bend policy | Direct filesystem/database access is outside the enforcement boundary |
| Small laws check | `bend PROOF.bend` reports ALL PROOFS CHECK for three laws | `--verdict` requires missing Lean v4.34.0; no universal registry soundness proof claimed |

## Main constraint: a mailbox is not attention

The shared tools support peer communication, but a queued message does not reliably start an idle Codex model turn. The baseline requires agents to call `inbox` at work boundaries. Claude can optionally use a custom channel started with explicit opt-in. Building automatic Codex attention likely requires a harness-owned app-server connection or a future native incoming-message surface. Resuming a stored thread is not proof of safe attachment to a live TUI.

That distinction determines the product promise: “agents can exchange visible messages without copy/paste” is supported by the transport spike; “all existing terminals autonomously react to each other” is not yet demonstrated.

## What Bend taught us

- Definitions are checked in order; the first helper arrangement was rejected for a forward/mutual recursive dependency. Nested pattern matching kept the membership traversal structurally recursive.
- A reused list requires the reusable quantity, `List<&2, Participant>`. Default `List<Participant>` is affine and cannot be reused for two membership checks.
- ES-module export is a direct practical integration path. Pure definitions accept documented constructor-shaped JS values.
- The three laws are deliberately small: empty registry rejection and the boolean gate's rejection of either missing membership. Integration tests cover the runtime examples; they are not substitutes for a general proof.

## Official integration evidence

- [Bend guide: JS imports and exports](https://github.com/bendlang/bend/blob/main/guide/GUIDE.md): documents `.mjs` exports of non-IO definitions and constructor representation.
- [Claude channels reference](https://code.claude.com/docs/en/channels-reference): custom-channel capability, notifications, development startup flag, interactive-session constraints, and absent processing acknowledgement.
- [Claude hooks](https://code.claude.com/docs/en/hooks): lifecycle and tool hooks; optional future registration integration.
- [Codex MCP](https://developers.openai.com/codex/mcp): stdio server configuration.
- [Codex App Server](https://developers.openai.com/codex/app-server): thread/turn control and MCP integration.
- [Codex MCP logging handler](https://github.com/openai/codex/blob/main/codex-rs/rmcp-client/src/logging_client_handler.rs): logging notifications route to tracing; this handler does not feed them into model context.
- Related official issues [#18056](https://github.com/openai/codex/issues/18056) and [#17543](https://github.com/openai/codex/issues/17543) discuss incoming peer-message support. Availability should be rechecked before implementation.

## Next live acceptance test

Start separately configured Claude Code and Codex terminals on the same repo. Ask Claude to request a bounded code review from Codex. Have Codex check its inbox, inspect the actual code, and reply with file references. Confirm both discovery and the visible conversation work, and record how much user prompting was needed. This tests the quality-of-life gain that protocol plumbing alone cannot establish.
