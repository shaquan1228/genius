let verifier ~(task : Task.t) =
  match task.criterion with
  | Criterion.Code { verifier } -> Some verifier
  | Criterion.Answer _ -> None

let case = Case.create
let reference ~(task : Task.t) = task.reference
