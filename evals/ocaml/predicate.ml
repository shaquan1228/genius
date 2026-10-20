(* Predicate: the assertion algebra every criterion compiles to. One evaluator grades
   file edits, structured replies, tool traces, and environment state.
   https://arxiv.org/abs/2307.13854 (WebArena: exact_match, must_include, located state)
   https://arxiv.org/abs/2406.13352 (AgentDojo: utility and security as separate predicates) *)
type t =
  | Present of { path : string list }
  | Equals of { path : string list; expected : Value.t }
  | Within of { path : string list; allowed : Value.t list }
  | Contains of { path : string list; item : Value.t }
  | Words of { path : string list; min_words : int; max_words : int }
  | All of { checks : (string * t) list }
  | Any of { checks : (string * t) list }
  | Not of { check : t }

let rec holds ~predicate ~observation =
  let at path accept = Option.fold ~none:false ~some:accept (Value.get ~value:observation ~path) in
  let member items value = List.exists (fun right -> Value.equal ~left:value ~right) items in
  match predicate with
  | Present { path } -> at path (( <> ) Value.Null)
  | Equals { path; expected } -> at path (fun value -> Value.equal ~left:value ~right:expected)
  | Within { path; allowed } ->
      at path (function Value.List { items } -> List.for_all (member allowed) items | _ -> false)
  | Contains { path; item } ->
      at path (function Value.List { items } -> member items item | _ -> false)
  | Words { path; min_words; max_words } ->
      at path (function
        | Value.String { value } ->
            let count = Support.word_count value in
            min_words <= count && count <= max_words
        | _ -> false)
  | All { checks } -> List.for_all (fun (_, check) -> holds ~predicate:check ~observation) checks
  | Any { checks } -> List.exists (fun (_, check) -> holds ~predicate:check ~observation) checks
  | Not { check } -> not (holds ~predicate:check ~observation)
