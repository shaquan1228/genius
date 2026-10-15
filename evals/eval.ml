(* Case assembly only. Fixtures, checks, scope, and references are explicit inputs. *)
type t = {
  id : string;
  fixture : Fixture.t;
  task : Task.t;
  checks : Check.t;
  allowed_files : string list;
  reference : Reference.t;
}

let case ~id ~fixture ~task ~checks ~allowed_files ~reference =
  { id; fixture; task; checks; allowed_files; reference }
