val case : Ast.case -> Ast.public_case
(** Validate a case before producing each consumer's immutable projection. *)

val verifier : Ast.case -> Ast.verifier option
val reference : Ast.case -> Ast.reference
