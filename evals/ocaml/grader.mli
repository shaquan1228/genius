(* Grader: pure logic applying criteria to responses and observed outcomes.
   IO, execution, and presentation remain harness responsibilities.
   https://developers.openai.com/api/docs/guides/graders
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents *)
val grade : Ast.case -> response:Ast.response option -> outcome:Ast.outcome -> Ast.score

(* Whitespace follows Python's Unicode str.split and str.strip. *)
val word_count : string -> int
val trim : string -> string
