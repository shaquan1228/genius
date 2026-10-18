type field_comparison = {
  name : string;
  before : Response_value.t option;
  after : Response_value.t option;
  equal : bool;
}

type t = { equal : bool; fields : field_comparison list }

module Fields = Map.Make (String)

let create ~before ~after =
  let index fields =
    List.fold_left
      (fun indexed (field : Response_field.t) ->
        if Fields.mem field.name indexed then indexed else Fields.add field.name field.value indexed)
      Fields.empty
      fields
  in
  let fields =
    Fields.merge
      (fun name before after -> Some { name; before; after; equal = before = after })
      (index before)
      (index after)
    |> Fields.bindings |> List.map snd
  in
  { equal = List.for_all (fun (field : field_comparison) -> field.equal) fields; fields }
