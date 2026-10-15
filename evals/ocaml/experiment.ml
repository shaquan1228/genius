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
    token_limit = 50_000;
    time_limit = 300;
    cache = false;
  }

let resolve ?(epochs = default.epochs) ?(message_limit = default.message_limit)
    ?(token_limit = default.token_limit) ?(time_limit = default.time_limit) ?(cache = default.cache)
    () =
  List.iter
    (fun (name, value) ->
      if value <= 0 then invalid_arg ("Experiment " ^ name ^ " must be positive"))
    [
      ("epochs", epochs);
      ("message_limit", message_limit);
      ("token_limit", token_limit);
      ("time_limit", time_limit);
    ];
  { Ast.profiles = default.profiles; epochs; message_limit; token_limit; time_limit; cache }
