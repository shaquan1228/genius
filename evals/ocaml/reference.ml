(* Reference constructor shared by code-case builders. Ast.reference defines the fields. *)
let edits files = { Ast.edits = files; completion = Plain "Reference edits applied." }
