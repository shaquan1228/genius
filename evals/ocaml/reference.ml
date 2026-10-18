(* Reference: reference output used for offline validation, distinct from a
   criterion's expected fields. Combining file edits and a completion is our mapping.
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
   https://evalscope.readthedocs.io/en/latest/advanced_guides/custom_dataset/llm.html *)
type t = { edits : Fixture.t; completion : Completion.t }

let create ~edits ~completion : t = { edits; completion }

let compare ~(before : t) ~(after : t) =
  Comparison.create
    ~fields:
      [
        ("edits", (Fixture.compare ~before:before.edits ~after:after.edits).equal);
        ("completion", (Completion.compare ~before:before.completion ~after:after.completion).equal);
      ]
