let instruction = Ast.make_instruction
let text_rule = Ast.make_text_rule

let rubric ~expected ~text_rule =
  Result.bind (Ast.make_response expected) (fun expected -> Ast.make_rubric ~expected ~text_rule)

let experiment ~profiles ~epochs ~message_limit ~cost_limit ~time_limit ~cache =
  Ast.make_experiment ~profiles ~epochs ?message_limit ~cost_limit ~time_limit ~cache ()
