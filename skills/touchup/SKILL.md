---
name: touchup
description: Make one small, local, reversible improvement to a durable artifact. Durable artifacts include scaffolding, docs, a comment, a rule list, config, or dead code. Use when a scaffold deviates from the sources that codify it, when a new pattern or lesson is worth writing down, when a note is narrower or wider than the truth, or when a doc points at something that is gone. Triggers on "touch up", "touchup", "note that", "add a rule for", "widen this comment", "document this pattern", "clean that up", "this drifted".
argument-hint: "[what to touch up; omit to use the latest lesson in the conversation]"
---

## Task

Make one touch: the smallest edit that brings one durable artifact in line with the truth. Put it in the file where that truth belongs. Leave everything else as it was.

## Context

- GNS-003 (smallest reversible action) sets the size. GNS-001 (observe before acting) picks the home. GNS-004 (independent premise validation) gates widening and deletion.
- If GNS-001..006 are not in context, read `../../docs/identity.md` relative to this file. In Claude Code, this is `$CLAUDE_PLUGIN_ROOT/docs/identity.md`. Load it inline. Do not prompt the user.
- With no argument, the touch is the latest lesson, decision, or "we should remember that" in the conversation. If there is none, ask once.
- `references/touch-kinds.md` defines the six kinds of touch and the evidence each one needs. Read it before you classify.
- `references/finding-the-home.md` ranks the sources and maps confusing repo layouts. Read it before you pick a file.
- `references/examples.md` holds touches to copy and traps to avoid. Read it for calibration.

## Rules

- One intent per touch. If the request holds two intents, make the first touch and list the second.
- Find the home before you write. Search for the fact first. Edit what exists before you add something new.
- Edit the file that deviates. Do not edit the source it deviates from.
- Rank sources by authority, not by nearness. Executable truth outranks codified docs. Codified docs outrank the majority of instances, and the majority outranks a single instance.
- If the codified sources disagree with each other, stop. Report the conflict as a fork. Do not pick a winner.
- Match the scope of the home to the scope of the fact. A repo-wide fact goes in the repo-wide doc. A fact about one package goes in that package's doc.
- Do not edit vendored, generated, archived, or historical files. These include changelogs and release notes. They record what was true.
- Do not widen a claim until a search shows the wider claim holds. Do not delete until a search shows nothing references the target.
- Do not invent a fact. Write only what you observed or what the user stated.
- Match the local voice: heading level, bullet style, casing, line width, and tone.
- Stay inside the budget: about three files, one hunk per file, and twenty changed lines. If the touch needs more, it is not a touch. Stop and hand off to `/genius:preflight`.
- Do not fix the typo two lines down. Put it under "seen, not touched".
- Do not name a tool you did not observe. Say "the repo's formatter" until you have seen it.

## Evaluate

The touch ships only if all of these hold:

- The edited file is the home that `references/finding-the-home.md` selects. The report cites the evidence for it.
- Every changed line serves the one intent. `git diff` or a re-read shows no other change.
- The fact is stated once. No second copy in another file now disagrees with it.
- Widening and deletion carry the search that justified them.
- Vendored, generated, archived, and historical files are byte-identical.
- The cheapest check that fits the touch ran and passed: a formatter, linter, link check, or test.
- The report fits the shape in Iterate step 7.

## Iterate

1. **Load.** Load the identity if absent. Read `references/touch-kinds.md` and `references/finding-the-home.md`.
2. **Name the intent.** State the touch in one sentence. With no argument, take it from the conversation.
3. **Find the home.** Search for the fact and its near-wordings. Classify each hit by authority and scope: executable, codified, instance, vendored, generated, or historical (GNS-001).
   - If the fact already exists in its home, the touch is a reword or nothing. Do not add a duplicate.
   - If codified sources conflict, report the fork and stop.
4. **Classify.** Pick one kind: widen, narrow, scaffold, rule, delete, or fix drift. Gather the evidence that kind requires (GNS-004).
5. **Size check.** Estimate files, hunks, and lines. Over budget means a hand-off, not a touch (GNS-003).
6. **Apply and check.** Make the edit in the local voice. Run the cheapest check that fits. Search again for copies of the fact that now disagree.
7. **Report.** One line per file changed, with the evidence for the home. Then "seen, not touched" for anything you noticed and left alone. Check the report against Evaluate.
