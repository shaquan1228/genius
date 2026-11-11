# Touch kinds

Each touch is exactly one kind. The kind decides what a correct edit looks like and what evidence must exist first. Without that evidence, there is no touch.

| Kind | Fires when | Evidence before the edit | The edit |
|---|---|---|---|
| **Widen** | A note, comment, or rule is narrower than the truth it describes | A search or read shows the wider claim holds in every case it will now cover | Reword the existing line. Do not add a second line. |
| **Narrow** | A rule overclaims and a real exception exists | The exception is observed in code, config, or a user statement | Add the exception to the existing line, or qualify its scope. |
| **Scaffold** | An instance deviates from the template, schema, or sibling majority, or a needed stub is missing | The codified source is named, and its requirement is quoted | Add or fix the missing part in the deviant instance, in the source's format. |
| **Rule** | A new pattern or lesson is worth codifying | The pattern appears in two or more places, or the user declared it. The rule is not already stated in its home. | One bullet in the existing rule list of the home. |
| **Delete** | A comment, doc line, or symbol points at something that is gone or unused | A search shows no remaining references, or shows the target is removed | Remove the stale lines only. Keep the surrounding structure valid. |
| **Fix drift** | A doc states a fact that changed: a path, command, flag, or name | The new truth is observed in the executable source | Replace the stale token. Keep the sentence. |

## Choosing between kinds

- A narrow note that is still true but incomplete is **widen**. A note that is now false is **fix drift**.
- A new pattern with an existing rule that almost covers it is **widen** of that rule, not a new **rule**.
- A missing section in one instance is **scaffold**. A missing section in every instance is a template change. That is not a touch, so hand it off.
- If two kinds both fit, the request holds two intents. Make the first touch and list the second.

## Not a touch

Hand these off to `/genius:preflight`. Do not shrink them to fit.

- The edit crosses more than about three files or twenty lines.
- The codified sources disagree, and resolving them is a decision.
- The fix changes behavior, not a description of behavior. One exception holds: deleting dead code a search proved unused.
- The touch needs a fact nobody observed or stated.
