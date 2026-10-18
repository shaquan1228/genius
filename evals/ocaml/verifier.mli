type t = private {
  inputs : string list;
  files : Artifact.t list;
  tools : Artifact.t list;
  command : string list;
  stdin : string;
  timeout_seconds : int;
}

val create :
  inputs:string list ->
  files:Artifact.t list ->
  tools:Artifact.t list ->
  command:string list ->
  stdin:string ->
  timeout_seconds:int ->
  (t, Validation_failure.t) result

val resolve_resources :
  verifier:t -> resources:Resource_binding.t list -> (t, Validation_failure.t) result

val compare : before:t -> after:t -> Comparison.t
