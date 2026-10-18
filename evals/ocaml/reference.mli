type t = { edits : Fixture.t; completion : Completion.t }

val create : edits:Fixture.t -> completion:Completion.t -> t
val compare : before:t -> after:t -> Comparison.t
