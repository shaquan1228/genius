let issue code field message values : Validation_issue.t = { code; field; message; values }

let checked ?case_id issues value =
  match issues with [] -> Ok value | _ -> Error { Validation_failure.case_id; issues }

let when_invalid condition problem = if condition then [] else [ problem ]
