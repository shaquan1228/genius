val default : Ast.experiment

val resolve :
  ?epochs:int ->
  ?message_limit:int ->
  ?token_limit:int ->
  ?time_limit:int ->
  ?cache:bool ->
  unit ->
  Ast.experiment
