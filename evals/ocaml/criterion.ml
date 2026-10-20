(* Criterion: a declarative success condition, applied by a grader rather than by
   the candidate. The code/structured-response distinction is this repository's design;
   state criteria follow state-based grading of tool-using agents.
   https://developers.openai.com/api/docs/guides/evals
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
   https://arxiv.org/abs/2406.12045 (tau-bench: final state and required outputs) *)
type t =
  | Code of { verifier : Verifier.t }
  | Answer of { rubric : Rubric.t }
  | State of { predicate : Predicate.t }

let create ?code ?answer ?state () =
  match (code, answer, state) with
  | Some value, None, None -> Ok (Code { verifier = value })
  | None, Some value, None -> Ok (Answer { rubric = value })
  | None, None, Some value -> Ok (State { predicate = value })
  | _ ->
      Error
        {
          Validation_failure.case_id = None;
          issues =
            [
              Validation.issue
                Validation_code.Invalid_alternative
                "criterion"
                "Criterion.create requires exactly one of code, answer, or state"
                [ "code"; "answer"; "state" ];
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
  | State a, State b ->
      Comparison.combine
        ~comparisons:[ ("state", Predicate.compare ~before:a.predicate ~after:b.predicate) ]
  | (Code _ | Answer _ | State _), _ -> Comparison.create ~fields:[ ("kind", false) ]

let condition ~criterion =
  match criterion with
  | Code _ ->
      Result.get_ok
        (Predicate.equals
           ~path:[ "verification" ]
           ~expected:(Value.String { value = Verification.name ~status:Verification.Passed }))
  | Answer { rubric } -> Rubric.predicate ~rubric
  | State { predicate } -> predicate
