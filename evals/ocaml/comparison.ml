type t = { equal : bool; changed_fields : string list }

let create ~fields =
  let changed_fields =
    List.filter_map (fun (name, equal) -> if equal then None else Some name) fields
  in
  { equal = changed_fields = []; changed_fields }

let combine ~comparisons =
  let changed_fields =
    List.concat_map
      (fun (name, comparison) ->
        List.map
          (fun field -> if field = "" then name else name ^ "." ^ field)
          comparison.changed_fields)
      comparisons
  in
  { equal = changed_fields = []; changed_fields }
