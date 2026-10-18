(* Instruction: task input describing the requested behavior. This prompt-only value
   maps to Hugging Face's instruction/query and OpenAI eval inputs.
   https://huggingface.co/docs/lighteval/main/en/package_reference/doc
   https://developers.openai.com/api/docs/guides/evals *)
type t = { skill : string; prompt : string }

let valid_name ~name =
  name <> ""
  && (match name.[0] with 'a' .. 'z' -> true | _ -> false)
  && String.for_all (function 'a' .. 'z' | '0' .. '9' | '-' -> true | _ -> false) name

let create ~skill ~prompt =
  Validation.checked
    (Validation.when_invalid
       (valid_name ~name:skill)
       (Validation.issue
          Validation_code.Invalid_identity
          "instruction.skill"
          "Invalid instruction skill"
          [ skill ]))
    { skill; prompt }

let compare ~(before : t) ~(after : t) =
  Comparison.create
    ~fields:[ ("skill", before.skill = after.skill); ("prompt", before.prompt = after.prompt) ]
