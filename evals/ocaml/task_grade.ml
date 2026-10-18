type t = { correctness : Correctness_grade.t; scope : Scope_grade.t; scores : Score.t }

let create ~(correctness : Correctness_grade.t) ~(scope : Scope_grade.t) =
  { correctness; scope; scores = [ ("correctness", correctness.passed); ("scope", scope.passed) ] }
