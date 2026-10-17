type t = private {
  profiles : Profile.t list;
  epochs : int;
  message_limit : int option;
  cost_limit : float;
  time_limit : int;
  cache : bool;
}

val default : t

val resolve :
  ?profiles:Profile.t list ->
  ?epochs:int ->
  ?message_limit:int ->
  ?cost_limit:float ->
  ?time_limit:int ->
  ?cache:bool ->
  unit ->
  (t, Validation_failure.t) result

val create :
  profiles:Profile.t list ->
  epochs:int ->
  message_limit:int option ->
  cost_limit:float ->
  time_limit:int ->
  cache:bool ->
  (t, Validation_failure.t) result
