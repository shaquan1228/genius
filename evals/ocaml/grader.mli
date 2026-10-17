(* Grader: pure logic applying criteria to responses and observed outcomes.
   IO, execution, and presentation remain harness responsibilities.
   https://developers.openai.com/api/docs/guides/graders
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents *)
(* Ordered mandatory boolean scores, derived from the grading definitions. *)
val required_names : string list

val grade :
  task:Task.t ->
  response:Response.t option ->
  outcome:Outcome.t ->
  (Score.t, Grading_failure.t) result

(* Whitespace follows Python's Unicode str.split and str.strip. *)
val word_count : text:string -> int
val trim : text:string -> string
