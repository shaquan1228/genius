val instruction : skill:string -> prompt:string -> (Ast.instruction, Ast.validation_failure) result

val text_rule :
  field:string -> min_words:int -> max_words:int -> (Ast.text_rule, Ast.validation_failure) result

val rubric :
  expected:(string * Ast.response_value) list ->
  text_rule:Ast.text_rule option ->
  (Ast.rubric, Ast.validation_failure) result

val experiment :
  profiles:Ast.profile list ->
  epochs:int ->
  message_limit:int option ->
  cost_limit:float ->
  time_limit:int ->
  cache:bool ->
  (Ast.experiment, Ast.validation_failure) result
