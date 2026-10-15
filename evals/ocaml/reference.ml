(* Reference: reference output used for offline validation, distinct from a
   criterion's expected fields. Combining file edits and a completion is our mapping.
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
   https://evalscope.readthedocs.io/en/latest/advanced_guides/custom_dataset/llm.html *)
type completion = Plain of string | Structured of Response.t
type t = { edits : Fixture.t; completion : completion }

let make ?(edits = Fixture.empty) completion = { edits; completion }
let edits files = make ~edits:files (Plain "Reference edits applied.")
