(* Shared typed examples for visible tests and trusted held-out checks. *)
let check ~name f examples =
  List.iter
    (fun (input, expected) ->
      if f input <> expected then failwith name)
    examples

let rejects ~name f inputs =
  List.iter
    (fun input ->
      try
        ignore (f input);
        failwith name
      with Invalid_argument _ -> ())
    inputs
