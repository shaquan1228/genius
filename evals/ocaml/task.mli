type t = private {
  id : string;
  fixture : Fixture.t;
  instruction : Instruction.t;
  criterion : Criterion.t;
  allowed_files : string list;
  reference : Reference.t;
}

val create :
  id:string ->
  fixture:Fixture.t ->
  instruction:Instruction.t ->
  criterion:Criterion.t ->
  allowed_files:string list ->
  reference:Reference.t ->
  (t, Validation_failure.t) result

val resolve_resources :
  task:t -> resources:Resource_binding.t list -> (t, Validation_failure.t) result

val required_scores : string list

val grade :
  task:t -> response:Response.t option -> outcome:Outcome.t -> (Score.t, Grading_failure.t) result

val verifier : task:t -> Verifier.t option
