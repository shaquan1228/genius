type profile = { name : string; preamble : string; instructions : string list }

type t = private {
  profiles : profile list;
  epochs : int;
  message_limit : int;
  token_limit : int;
  time_limit : int;
  cache : bool;
}

val default : t

val resolve :
  ?epochs:int ->
  ?message_limit:int ->
  ?token_limit:int ->
  ?time_limit:int ->
  ?cache:bool ->
  unit ->
  t
