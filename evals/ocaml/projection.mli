val case : Ast.task -> Ast.case
(** Validate a case before producing each consumer's immutable projection. *)

val verifier : Ast.task -> Ast.verifier option
val reference : Ast.task -> Ast.reference
