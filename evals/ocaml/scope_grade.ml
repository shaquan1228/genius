type t = { passed : bool; unexpected_files : string list }

let create ~allowed_files ~changed_files =
  let unexpected_files =
    List.sort_uniq
      String.compare
      (List.filter (fun path -> not (List.mem path allowed_files)) changed_files)
  in
  { passed = unexpected_files = []; unexpected_files }
