val empty : Ast.fixture
(** Immutable file collections with duplicate detection and explicit overlays. *)

val of_files : (string * string) list -> (Ast.fixture, Ast.validation_failure) result

val add :
  path:string -> contents:string -> Ast.fixture -> (Ast.fixture, Ast.validation_failure) result

val overlay : Ast.fixture -> overrides:Ast.fixture -> Ast.fixture
val files : Ast.fixture -> (string * string) list
