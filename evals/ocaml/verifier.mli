val valid_path : string -> bool
val validate : Ast.verifier -> Ast.verifier

val make :
  inputs:string list ->
  files:(string * Ast.content) list ->
  tools:(string * Ast.content) list ->
  command:string list ->
  stdin:string ->
  timeout_seconds:int ->
  Ast.verifier
