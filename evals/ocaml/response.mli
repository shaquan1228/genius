val empty : Ast.response
(** Validate unique, nonempty names without changing field order. *)

val of_fields : (string * Ast.response_value) list -> (Ast.response, Ast.validation_failure) result
val fields : Ast.response -> (string * Ast.response_value) list
