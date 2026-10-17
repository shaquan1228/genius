val empty : Ast.fixture
val add : fixture:Ast.fixture -> file:Ast.file -> (Ast.fixture, Ast.validation_failure) result
val overlay : base:Ast.fixture -> overrides:Ast.fixture -> Ast.fixture
val files : fixture:Ast.fixture -> Ast.file list
