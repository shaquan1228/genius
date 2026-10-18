(* Text rule: this repository's bounded-word criterion for one string field; the
   sources establish configurable success criteria, not this particular rule schema.
   https://developers.openai.com/api/docs/guides/evals
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents *)
type t = { field : string; min_words : int; max_words : int }

let create ~field ~min_words ~max_words =
  Validation.checked
    (Validation.when_invalid
       (field <> "" && min_words >= 0 && max_words >= min_words)
       (Validation.issue
          Validation_code.Invalid_text_rule
          "text_rule"
          "Invalid text rule"
          [ field ]))
    { field; min_words; max_words }

let word_count = Text.word_count
