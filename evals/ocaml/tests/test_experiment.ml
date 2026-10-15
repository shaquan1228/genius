let () =
  let experiment = Experiment.default in
  assert (experiment.epochs = 5);
  assert (experiment.message_limit = 40);
  assert (experiment.token_limit = 50_000);
  assert (experiment.time_limit = 300);
  assert (not experiment.cache);
  match experiment.profiles with
  | [ baseline; genius ] ->
      assert (baseline.name = "baseline");
      assert (baseline.preamble = "");
      assert (baseline.instructions = []);
      assert (genius.name = "genius");
      assert (genius.instructions = [ "docs"; "skills" ]);
      assert (
        genius.preamble
        = "Read ../instructions/skills/{skill}/SKILL.md and its referenced files. Apply that skill \
           to this task.\n\n")
  | _ -> assert false

let () =
  assert (Experiment.resolve () = Experiment.default);
  let resolved =
    Experiment.resolve ~epochs:2 ~message_limit:8 ~token_limit:900 ~time_limit:10 ~cache:true ()
  in
  assert (resolved.epochs = 2);
  assert (resolved.message_limit = 8);
  assert (resolved.token_limit = 900);
  assert (resolved.time_limit = 10);
  assert resolved.cache;
  assert (resolved.profiles = Experiment.default.profiles);
  assert (Experiment.default.epochs = 5);
  List.iter
    (fun resolve ->
      List.iter
        (fun value ->
          match resolve value with _ -> assert false | exception Invalid_argument _ -> ())
        [ 0; -1; min_int ])
    [
      (fun value -> Experiment.resolve ~epochs:value ());
      (fun value -> Experiment.resolve ~message_limit:value ());
      (fun value -> Experiment.resolve ~token_limit:value ());
      (fun value -> Experiment.resolve ~time_limit:value ());
    ]
