(* Validated, immutable projections for each consumer. *)
let verifier (case : Ast.task) =
  match case.criterion with Ast.Code verifier -> Some verifier | Ast.Answer _ -> None

let case (case : Ast.task) : Ast.case =
  let tools =
    match case.criterion with Ast.Code verifier -> verifier.tools | Ast.Answer _ -> []
  in
  {
    id = case.id;
    skill = case.instruction.skill;
    prompt = case.instruction.prompt;
    files =
      List.map (fun (path, text) -> (path, Ast.Inline text)) (Fixture.files case.fixture) @ tools;
  }

let reference (case : Ast.task) = case.reference
