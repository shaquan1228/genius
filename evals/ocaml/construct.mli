val file : path:string -> contents:string -> (Ast.file, Ast.validation_failure) result
val artifact : path:string -> content:Ast.content -> (Ast.artifact, Ast.validation_failure) result
val resource_binding : key:string -> contents:string -> Ast.resource_binding
val fixture : files:Ast.file list -> (Ast.fixture, Ast.validation_failure) result

val response_field :
  name:string -> value:Ast.response_value -> (Ast.response_field, Ast.validation_failure) result

val response : fields:Ast.response_field list -> (Ast.response, Ast.validation_failure) result
val instruction : skill:string -> prompt:string -> (Ast.instruction, Ast.validation_failure) result

val text_rule :
  field:string -> min_words:int -> max_words:int -> (Ast.text_rule, Ast.validation_failure) result

val rubric :
  expected:Ast.response ->
  text_rule:Ast.text_rule option ->
  (Ast.rubric, Ast.validation_failure) result

val verifier :
  inputs:string list ->
  files:Ast.artifact list ->
  tools:Ast.artifact list ->
  command:string list ->
  stdin:string ->
  timeout_seconds:int ->
  (Ast.verifier, Ast.validation_failure) result

val task :
  id:string ->
  fixture:Ast.fixture ->
  instruction:Ast.instruction ->
  criterion:Ast.criterion ->
  allowed_files:string list ->
  reference:Ast.reference ->
  (Ast.task, Ast.validation_failure) result

val experiment :
  profiles:Ast.profile list ->
  epochs:int ->
  message_limit:int option ->
  cost_limit:float ->
  time_limit:int ->
  cache:bool ->
  (Ast.experiment, Ast.validation_failure) result
