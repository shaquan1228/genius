type t = private { passed : bool; answer : Rubric_grade.t option; verification : Verification.t }

val create :
  answer:Rubric_grade.t option -> verification:Verification.t -> (t, Grading_failure.t) result
