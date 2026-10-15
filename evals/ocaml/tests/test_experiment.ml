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
