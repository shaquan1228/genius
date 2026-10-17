(* Fixture: initial-state files. This immutable collection is our file-based mapping
   of sample files and task environments, not a universal evaluation fixture schema.
   https://inspect.aisi.org.uk/datasets.html#sample-files
   https://docs.harborframework.com/tasks/environment *)
module Files = Fixture_store

let empty : Ast.fixture = Files.empty

let add ~path ~contents fixture =
  if Files.mem path fixture then invalid_arg ("Duplicate fixture path: " ^ path);
  Files.add path contents fixture

let of_files files =
  List.fold_left (fun fixture (path, contents) -> add ~path ~contents fixture) empty files

let overlay base ~overrides = Files.overlay base overrides
let files = Files.files
