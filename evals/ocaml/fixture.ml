module Files = Map.Make (String)
type t = string Files.t

let empty = Files.empty

let add ~path ~contents fixture =
  if Files.mem path fixture then invalid_arg ("Duplicate fixture path: " ^ path);
  Files.add path contents fixture

let of_files files =
  List.fold_left (fun fixture (path, contents) -> add ~path ~contents fixture) empty files

let overlay base overrides = Files.union (fun _ _ replacement -> Some replacement) base overrides
let files = Files.bindings
