type t = private { correctness : Correctness_grade.t; scope : Scope_grade.t; scores : Score.t }

val create : correctness:Correctness_grade.t -> scope:Scope_grade.t -> t
