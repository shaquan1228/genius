(* Value: one JSON-shaped domain for inputs, expectations, and observations, so tasks
   state goals over files, tool traces, database state, or structured replies alike.
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

(* Record fields compare without order; the first duplicate wins. *)
let rec equal ~left ~right =
  let names fields = List.sort_uniq String.compare (List.map fst fields) in
  match (left, right) with
  | Record { fields = l }, Record { fields = r } ->
      names l = names r
      && List.for_all
           (fun name -> equal ~left:(List.assoc name l) ~right:(List.assoc name r))
           (names l)
  | List { items = l }, List { items = r } -> List.equal (fun left right -> equal ~left ~right) l r
  | _ -> left = right
