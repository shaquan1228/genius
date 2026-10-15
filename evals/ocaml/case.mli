val validate : Ast.case -> Ast.case

val make :
  id:string ->
  fixture:Fixture.t ->
  instruction:Ast.instruction ->
  criterion:Ast.criterion ->
  allowed_files:string list ->
  reference:Ast.reference ->
  Ast.case
