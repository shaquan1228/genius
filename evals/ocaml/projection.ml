(* Validated, immutable projections for each consumer. *)
let verifier (case : Ast.case) =
  match (Case.validate case).criterion with
  | Ast.Code verifier -> Some verifier
  | Ast.Answer _ -> None

let case (case : Ast.case) : Ast.public_case =
  let case = Case.validate case in
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

let reference (case : Ast.case) = (Case.validate case).reference
