type t = private {
  equal : bool;
  id : Comparison.t;
  fixture : Fixture_comparison.t;
  instruction : Comparison.t;
  criterion : Comparison.t;
  allowed_files : Comparison.t;
  reference : Comparison.t;
}

val create :
  id:Comparison.t ->
  fixture:Fixture_comparison.t ->
  instruction:Comparison.t ->
  criterion:Comparison.t ->
  allowed_files:Comparison.t ->
  reference:Comparison.t ->
  t
