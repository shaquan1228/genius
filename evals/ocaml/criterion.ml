let answer ?text_rule ~expected () =
  Result.map (fun rubric -> Ast.Answer rubric) (Ast.make_rubric ~expected ~text_rule)
