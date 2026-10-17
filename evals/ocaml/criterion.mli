val answer :
  ?text_rule:Ast.text_rule ->
  expected:Ast.response ->
  unit ->
  (Ast.criterion, Ast.validation_failure) result
