val validate : Ast.task -> Ast.task

val make :
  id:string ->
  fixture:Ast.fixture ->
  instruction:Ast.instruction ->
  criterion:Ast.criterion ->
  allowed_files:string list ->
  reference:Ast.reference ->
  Ast.task
