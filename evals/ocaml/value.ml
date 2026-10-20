(* Value: the universal observation and expectation domain. One JSON-shaped,
   structurally comparable value lets tasks state goals over any environment:
   files, tool traces, database state, or structured replies.
   https://arxiv.org/abs/2406.12045 (tau-bench grades a final database state)
   https://arxiv.org/abs/2307.13854 (WebArena grades answers and located page state) *)
type t =
  | Null
  | Bool of { value : bool }
  | Int of { value : int }
  | Float of { value : float }
  | String of { value : string }
  | List of { items : t list }
  | Record of { fields : (string * t) list }

let strings ~values = List { items = List.map (fun value -> String { value }) values }

let rec get ~value ~path =
  match (path, value) with
  | [], _ -> Some value
  | name :: rest, Record { fields } ->
      Option.bind (List.assoc_opt name fields) (fun value -> get ~value ~path:rest)
  | _ :: _, _ -> None

let normalize fields =
  List.fold_left
    (fun kept (name, value) -> if List.mem_assoc name kept then kept else (name, value) :: kept)
    []
    fields
  |> List.sort (fun (left, _) (right, _) -> String.compare left right)

let rec equal ~left ~right =
  match (left, right) with
  | Record { fields = left }, Record { fields = right } ->
      List.equal
        (fun (name, left) (other, right) -> name = other && equal ~left ~right)
        (normalize left)
        (normalize right)
  | List { items = left }, List { items = right } ->
      List.equal (fun left right -> equal ~left ~right) left right
  | _ -> left = right
