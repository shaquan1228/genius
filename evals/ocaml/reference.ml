type t = { edits : Fixture.t; completion : Completion.t }

let create ~edits ~completion : t = { edits; completion }

let compare ~(before : t) ~(after : t) =
  Comparison.create
    ~fields:
      [
        ("edits", (Fixture.compare ~before:before.edits ~after:after.edits).equal);
        ("completion", (Completion.compare ~before:before.completion ~after:after.completion).equal);
      ]
