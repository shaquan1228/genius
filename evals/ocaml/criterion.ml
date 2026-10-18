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

let grade ~criterion ~response ~verification =
  let answer =
    match criterion with
    | Code _ -> None
    | Answer { rubric } -> Some (Rubric.grade ~rubric ~response)
  in
  Correctness_grade.create ~answer ~verification
