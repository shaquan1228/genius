val validate : Ast.case -> Ast.case

val make :
  id:string ->
  fixture:Ast.fixture ->
  instruction:Ast.instruction ->
  criterion:Ast.criterion ->
  allowed_files:string list ->
  reference:Ast.reference ->
  Ast.case
