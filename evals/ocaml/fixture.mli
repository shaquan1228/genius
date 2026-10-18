(* Fixture: immutable initial files. The map implementation belongs to Fixture.
   https://inspect.aisi.org.uk/datasets.html#sample-files
   https://docs.harborframework.com/tasks/environment *)
type t

val create : files:File.t list -> (t, Validation_failure.t) result
val empty : t
val add : fixture:t -> file:File.t -> (t, Validation_failure.t) result
val overlay : base:t -> overrides:t -> t
val files : fixture:t -> File.t list
val compare : before:t -> after:t -> Fixture_comparison.t
