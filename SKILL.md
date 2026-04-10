---
name: genius
description: Toggle genius engineering identity injection on or off for this session. Use `/genius on` to activate and `/genius off` to deactivate.
---

When the user runs `/genius on` or `/genius off`, follow the instructions below exactly.

## /genius on

Write a delimited block to `~/.claude/CLAUDE.md` that injects the genius engineering identity. If the file doesn't exist, create it. If a `# BEGIN GENIUS ... # END GENIUS` block already exists, replace it.

The block to write:

```
# BEGIN GENIUS
@<absolute path to docs/identity.md in this repo>
# END GENIUS
```

To get the absolute path, resolve it relative to this SKILL.md file's location. Confirm after writing: "genius identity active."

## /genius off

Remove the `# BEGIN GENIUS ... # END GENIUS` block from `~/.claude/CLAUDE.md`, including both markers and everything between them. Leave the rest of the file untouched. If the block doesn't exist, say so. Confirm after removal: "genius identity removed."
