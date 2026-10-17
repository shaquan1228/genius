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
