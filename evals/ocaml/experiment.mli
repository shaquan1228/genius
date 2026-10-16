val default : Ast.experiment

val resolve :
  ?epochs:int ->
  ?message_limit:int ->
  ?cost_limit:float ->
  ?time_limit:int ->
  ?cache:bool ->
  unit ->
  Ast.experiment
