(* Predicate: a declarative success condition over an observation. Grading is the
   evaluation of a small assertion algebra, so one kernel grades file edits,
   structured replies, tool traces, and environment state alike.
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

let path_issues ~field path =
  Validation.when_invalid
    (path <> [] && List.for_all (( <> ) "") path)
    (Validation.issue
       Validation_code.Invalid_predicate
       field
       "Predicate paths need nonempty segments"
       path)

let located ~field path value = Validation.checked (path_issues ~field path) value
let present ~path = located ~field:"present.path" path (Present { path })
let equals ~path ~expected = located ~field:"equals.path" path (Equals { path; expected })
let within ~path ~allowed = located ~field:"within.path" path (Within { path; allowed })
let contains ~path ~item = located ~field:"contains.path" path (Contains { path; item })

let words ~path ~min_words ~max_words =
  Validation.checked
    (path_issues ~field:"words.path" path
    @ Validation.when_invalid
        (0 <= min_words && min_words <= max_words)
        (Validation.issue
           Validation_code.Invalid_predicate
           "words"
           "Word bounds need 0 <= min_words <= max_words"
           [ string_of_int min_words; string_of_int max_words ]))
    (Words { path; min_words; max_words })

let named ~field checks value =
  let names = List.map fst checks in
  Validation.checked
    (Validation.when_invalid
       (List.for_all (( <> ) "") names
       && List.length names = List.length (List.sort_uniq String.compare names))
       (Validation.issue
          Validation_code.Invalid_identity
          field
          "Checks require unique, nonempty names"
          names))
    value

let all ~checks = named ~field:"all.checks" checks (All { checks })
let any ~checks = named ~field:"any.checks" checks (Any { checks })
let not_ ~check = Not { check }

let rec holds ~predicate ~observation =
  let observed path = Value.get ~value:observation ~path in
  let matches path accept = match observed path with Some value -> accept value | None -> false in
  let member items value = List.exists (fun other -> Value.equal ~left:value ~right:other) items in
  match predicate with
  | Present { path } -> matches path (( <> ) Value.Null)
  | Equals { path; expected } -> matches path (fun value -> Value.equal ~left:value ~right:expected)
  | Within { path; allowed } ->
      matches path (function
        | Value.List { items } -> List.for_all (member allowed) items
        | _ -> false)
  | Contains { path; item } ->
      matches path (function Value.List { items } -> member items item | _ -> false)
  | Words { path; min_words; max_words } ->
      matches path (function
        | Value.String { value } ->
            let count = Text.word_count ~text:value in
            min_words <= count && count <= max_words
        | _ -> false)
  | All { checks } -> List.for_all (fun (_, check) -> holds ~predicate:check ~observation) checks
  | Any { checks } -> List.exists (fun (_, check) -> holds ~predicate:check ~observation) checks
  | Not { check } -> not (holds ~predicate:check ~observation)

let compare ~before ~after = Comparison.create ~fields:[ ("predicate", before = after) ]
