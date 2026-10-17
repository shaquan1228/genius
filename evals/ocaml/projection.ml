let verifier ~(task : Ast.task) =
  match task.criterion with Ast.Code { verifier } -> Some verifier | Ast.Answer _ -> None

let case = Ast.project_case
let reference ~(task : Ast.task) = task.reference
