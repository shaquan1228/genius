(* Criterion: a declarative success condition, applied by a grader rather than by
   the candidate. The code/structured-response distinction is this repository's design.
   https://developers.openai.com/api/docs/guides/evals
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents *)
(* Text rule: this repository's bounded-word criterion for one string field; the
   sources establish configurable success criteria, not this particular rule schema.
   https://developers.openai.com/api/docs/guides/evals
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents *)
type text_rule = { field : string; min_words : int; max_words : int }
type answer = { expected : Response.t; text_rule : text_rule option }
type t = Code of Verifier.t | Answer of answer

let text_rule ~field ~min_words ~max_words =
  if field = "" || min_words < 0 || max_words < min_words then invalid_arg "Invalid text rule";
  { field; min_words; max_words }

let answer ?text_rule ~expected () =
  (match text_rule with
  | Some rule ->
      if rule.field = "" || rule.min_words < 0 || rule.max_words < rule.min_words then
        invalid_arg "Invalid text rule";
      if List.mem_assoc rule.field (Response.fields expected) then
        invalid_arg "Text rule overlaps expected fields"
  | None -> ());
  if Response.fields expected = [] && text_rule = None then
    invalid_arg "Answer criterion cannot be empty";
  Answer { expected; text_rule }

let ocaml ~sources ~assertions =
  if sources = [] || assertions = [] then invalid_arg "OCaml checks need sources and assertions";
  let assertions = List.map (fun condition -> "assert (" ^ condition ^ ")") assertions in
  Code
    (Verifier.make
       ~inputs:sources
       ~files:[ ("ocaml_verifier.py", Verifier.Resource "ocaml_verifier.py") ]
       ~tools:[ ("check.sh", Verifier.Resource "check.sh") ]
       ~command:([ "python3"; "-I"; "ocaml_verifier.py" ] @ sources)
       ~stdin:("let () =\n  " ^ String.concat ";\n  " assertions ^ "\n")
       ~timeout_seconds:30)
