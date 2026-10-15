(* Consumer projections exclude reference and private verifier data from agent inputs. *)
type public_case = private {
  id : string;
  skill : string;
  prompt : string;
  files : (string * Verifier.content) list;
}

val case : Ast.case -> public_case
val verifier : Ast.case -> Verifier.t option
val reference : Ast.case -> Ast.reference
