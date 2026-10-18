(* Reference: reference output used for offline validation, distinct from a
   criterion's expected fields. Combining file edits and a completion is our mapping.
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
   https://evalscope.readthedocs.io/en/latest/advanced_guides/custom_dataset/llm.html *)
type t = { edits : Fixture.t; completion : Completion.t }

val create : edits:Fixture.t -> completion:Completion.t -> t
val compare : before:t -> after:t -> Comparison.t
