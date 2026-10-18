type t = {
  equal : bool;
  added : File.t list;
  removed : File.t list;
  modified : (File.t * File.t) list;
}

module Files = Map.Make (String)

let create ~before ~after =
  let index files =
    List.fold_left
      (fun indexed (file : File.t) ->
        if Files.mem file.path indexed then indexed else Files.add file.path file indexed)
      Files.empty
      files
  in
  let before_index = index before and after_index = index after in
  let absent indexed (file : File.t) = not (Files.mem file.path indexed) in
  let added = List.filter (absent before_index) after in
  let removed = List.filter (absent after_index) before in
  let modified =
    List.filter_map
      (fun (file : File.t) ->
        match Files.find_opt file.path after_index with
        | Some other when file <> other -> Some (file, other)
        | Some _ | None -> None)
      before
  in
  { equal = added = [] && removed = [] && modified = []; added; removed; modified }
