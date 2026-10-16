(* Validating constructors for Ast.criterion. *)
let answer ?text_rule ~expected () =
  let expected = Response.of_fields expected in
  (match (text_rule : Ast.text_rule option) with
  | Some rule ->
      if rule.field = "" || rule.min_words < 0 || rule.max_words < rule.min_words then
        invalid_arg "Invalid text rule";
      if List.mem_assoc rule.field (Response.fields expected) then
        invalid_arg "Text rule overlaps expected fields"
  | None -> ());
  if Response.fields expected = [] && text_rule = None then
    invalid_arg "Answer criterion cannot be empty";
  Ast.Answer { expected; text_rule }

let validate = function
  | Ast.Code verifier -> Ast.Code (Verifier.validate verifier)
  | Ast.Answer criterion -> answer ?text_rule:criterion.text_rule ~expected:criterion.expected ()
