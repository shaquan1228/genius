type t = { passed : bool; answer : Rubric_grade.t option; verification : Verification.t }

let create ~(answer : Rubric_grade.t option) ~verification =
  match (answer, verification) with
  | Some grade, _ -> Ok { passed = grade.passed; answer; verification }
  | None, Verification.Harness_error { detail } ->
      Error (Grading_failure.Verification_harness_error { detail })
  | None, _ -> Ok { passed = verification = Verification.Passed; answer; verification }
