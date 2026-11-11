# Finding the home

The home is the single file where a fact belongs. A touch in the wrong file costs more than no touch. It leaves the true home stale and adds a second copy that will drift.

## Authority ranking

Sources that codify a convention rank in this order. A lower-ranked source that disagrees with a higher one is the deviant. The deviant gets the edit.

1. **Executable truth.** Code, config, schemas, CI, and test assertions. This is what the repo does.
2. **Codified docs.** Templates, contributor guides, agent instruction files, and lint or format config. This is what the repo says to do.
3. **Instance majority.** What most sibling instances do, when no codified doc speaks.
4. **Single instance.** One file's own choice. It never overrides the ranks above it.

Two sources at the same rank that disagree form a fork. Report it and stop. One exception holds: if one source points to the other ("see AGENTS.md"), the pointed-to source is the home.

## Classify each search hit

| Class | Recognize it by | Touch it? |
|---|---|---|
| Canonical | Named by a pointer, at the root of its scope, or listed in the contributor guide | Yes. This is the home. |
| Scoped | Lives in a package or subdirectory and governs only that subtree | Only for facts about that subtree |
| Pointer | Mostly says "see X" | No. Edit X. |
| Vendored | `vendor/`, `third_party/`, `node_modules/`, or a copied upstream with its own license | Never |
| Generated | `build/`, `dist/`, `out/`, `gen/`, a "do not edit" header, or listed in `.gitignore` | Never. Edit the generator's input. |
| Archived | `archive/`, `legacy/`, `old/`, `deprecated/`, or marked superseded | Never |
| Historical | Changelogs, release notes, ADRs, and migration logs | Never. They record what was true then. |

## Confusing layouts

- **Template and instances.** If one instance deviates from the template and its siblings, fix the instance. If the template disagrees with executable truth, that is a fork. Report it.
- **Nested instruction files.** A root `AGENTS.md` or `CLAUDE.md` governs the repo, and a package file governs only its package. A repo-wide fact goes at the root. A package fact goes in the package file. If no package file exists, use the root and name the scope in the line.
- **Pointer files.** When one instruction file only says "see X", the rule goes in X.
- **Mirrors.** `docs/` and a generated `site/` or `website/` copy have the same content. Edit the source the build reads.
- **Legacy twins.** `src/x.py` and `legacy/x.py`, or `v1/` and `v2/`, can look identical. Edit the copy that imports, CI, or the package manifest reach. Leave the other one alone.
- **Same-name files.** Several `README.md` or `SKILL.md` files can match. Pick the one whose directory owns the subject. Do not pick the first search hit.

## Scope test

Before you write, finish this sentence: "This fact is true for every file under ___." The blank names the directory whose doc is the home. If the blank is the repo root, the home is the root doc.
