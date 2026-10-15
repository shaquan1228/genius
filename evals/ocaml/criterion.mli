val answer : ?text_rule:Ast.text_rule -> expected:Ast.response -> unit -> Ast.criterion
val ocaml : sources:string list -> assertions:string list -> Ast.criterion
val validate : Ast.criterion -> Ast.criterion
