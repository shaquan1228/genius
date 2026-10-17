val make :
  id:string ->
  fixture:Ast.fixture ->
  instruction:Ast.instruction ->
  criterion:Ast.criterion ->
  allowed_files:string list ->
  reference:Ast.reference ->
  (Ast.task, Ast.validation_failure) result

val resolve_resources :
  Ast.task -> resources:(string * string) list -> (Ast.task, Ast.validation_failure) result
