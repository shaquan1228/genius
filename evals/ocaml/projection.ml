(* Consumer projections exclude reference and private verifier data from agent inputs. *)
type public_case = {
  id : string;
  skill : string;
  prompt : string;
  files : (string * Verifier.content) list;
}

let verifier (case : Ast.case) =
  match (Case.validate case).criterion with
  | Ast.Code verifier -> Some verifier
  | Ast.Answer _ -> None

let case (case : Ast.case) =
  let case = Case.validate case in
  let tools =
    match case.criterion with Ast.Code verifier -> verifier.tools | Ast.Answer _ -> []
  in
  {
    id = case.id;
    skill = case.instruction.skill;
    prompt = case.instruction.prompt;
    files =
      List.map (fun (path, text) -> (path, Verifier.Inline text)) (Fixture.files case.fixture)
      @ tools;
  }

let reference (case : Ast.case) = (Case.validate case).reference
