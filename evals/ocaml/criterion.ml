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

let ocaml ~sources ~assertions =
  if sources = [] || assertions = [] then invalid_arg "OCaml checks need sources and assertions";
  let assertions = List.map (fun condition -> "assert (" ^ condition ^ ")") assertions in
  Ast.Code
    (Verifier.make
       ~inputs:sources
       ~files:[ ("verifier.py", Ast.Resource "verifier.py") ]
       ~tools:[ ("check.sh", Ast.Resource "check.sh") ]
       ~command:([ "python3"; "-I"; "verifier.py"; "ocaml" ] @ sources)
       ~stdin:("let () =\n  " ^ String.concat ";\n  " assertions ^ "\n")
       ~timeout_seconds:30)

let validate = function
  | Ast.Code verifier -> Ast.Code (Verifier.validate verifier)
  | Ast.Answer criterion -> answer ?text_rule:criterion.text_rule ~expected:criterion.expected ()
