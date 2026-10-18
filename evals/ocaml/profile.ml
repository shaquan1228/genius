type t = { name : string; preamble : string; instructions : string list }

let create ~name ~preamble ~instructions : t = { name; preamble; instructions }

let compare ~(before : t) ~(after : t) =
  Comparison.create
    ~fields:
      [
        ("name", before.name = after.name);
        ("preamble", before.preamble = after.preamble);
        ( "instructions",
          List.sort_uniq String.compare before.instructions
          = List.sort_uniq String.compare after.instructions );
      ]
