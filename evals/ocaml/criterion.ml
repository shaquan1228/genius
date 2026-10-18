(* Criterion: a declarative success condition, applied by a grader rather than by
   the candidate. The code/structured-response distinction is this repository's design.
   https://developers.openai.com/api/docs/guides/evals
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents *)
type t = Code of { verifier : Verifier.t } | Answer of { rubric : Rubric.t }

let create ?code ?answer () =
  match (code, answer) with
  | Some value, None -> Ok (Code { verifier = value })
  | None, Some value -> Ok (Answer { rubric = value })
  | _ ->
      Error
        {
          Validation_failure.case_id = None;
          issues =
            [
              Validation.issue
                Validation_code.Invalid_alternative
                "criterion"
                "Criterion.create requires exactly one of code or answer"
                [ "code"; "answer" ];
            ];
        }

let compare ~before ~after =
  match (before, after) with
  | Code a, Code b ->
      Comparison.combine
        ~comparisons:[ ("verifier", Verifier.compare ~before:a.verifier ~after:b.verifier) ]
  | Answer a, Answer b ->
      Comparison.combine
        ~comparisons:[ ("rubric", Rubric.compare ~before:a.rubric ~after:b.rubric) ]
  | Code _, Answer _ | Answer _, Code _ -> Comparison.create ~fields:[ ("kind", false) ]
