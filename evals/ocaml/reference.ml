type t = { edits : Fixture.t; completion : Completion.t }

let create ~edits ~completion : t = { edits; completion }
