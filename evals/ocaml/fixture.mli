val empty : Ast.fixture
(** Immutable file collections with duplicate detection and explicit overlays. *)

val of_files : (string * string) list -> Ast.fixture
val add : path:string -> contents:string -> Ast.fixture -> Ast.fixture
val overlay : Ast.fixture -> overrides:Ast.fixture -> Ast.fixture
val files : Ast.fixture -> (string * string) list
