type content = Inline of string | Resource of string

type t = private {
  inputs : string list;
  files : (string * content) list;
  tools : (string * content) list;
  command : string list;
  stdin : string;
  timeout_seconds : int;
}

val valid_path : string -> bool

val make :
  inputs:string list ->
  files:(string * content) list ->
  tools:(string * content) list ->
  command:string list ->
  stdin:string ->
  timeout_seconds:int ->
  t
