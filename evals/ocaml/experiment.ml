let default : Ast.experiment =
  {
    profiles =
      [
        { name = "baseline"; preamble = ""; instructions = [] };
        {
          name = "genius";
          preamble =
            "Read ../instructions/skills/{skill}/SKILL.md and its referenced files. Apply that \
             skill to this task.\n\n";
          instructions = [ "docs"; "skills" ];
        };
      ];
    epochs = 5;
    message_limit = 40;
    cost_limit = 0.25;
    time_limit = 300;
    cache = false;
  }

let resolve ?(epochs = default.epochs) ?(message_limit = default.message_limit)
    ?(cost_limit = default.cost_limit) ?(time_limit = default.time_limit) ?(cache = default.cache)
    () =
  List.iter
    (fun (name, value) ->
      if value <= 0 then invalid_arg ("Experiment " ^ name ^ " must be positive"))
    [ ("epochs", epochs); ("message_limit", message_limit); ("time_limit", time_limit) ];
  if (not (Float.is_finite cost_limit)) || cost_limit <= 0. then
    invalid_arg "Experiment cost_limit must be finite and positive";
  { Ast.profiles = default.profiles; epochs; message_limit; cost_limit; time_limit; cache }
