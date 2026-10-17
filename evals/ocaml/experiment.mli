val default : Ast.experiment

val resolve :
  ?profiles:Ast.profile list ->
  ?epochs:int ->
  ?message_limit:int ->
  ?cost_limit:float ->
  ?time_limit:int ->
  ?cache:bool ->
  unit ->
  (Ast.experiment, Ast.validation_failure) result
