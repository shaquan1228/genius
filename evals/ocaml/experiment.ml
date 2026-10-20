(* Experiment: the measurement settings a run is executed under. *)
type t = {
  profiles : Profile.t list;
  epochs : int;
  message_limit : int option;
  cost_limit : float;
  time_limit : int;
  cache : bool;
}

let default : t =
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
    message_limit = None;
    cost_limit = 0.25;
    time_limit = 300;
    cache = false;
  }

let resolve ?(profiles = default.profiles) ?(epochs = default.epochs) ?message_limit
    ?(cost_limit = default.cost_limit) ?(time_limit = default.time_limit) ?(cache = default.cache)
    () =
  Support.checked
    [
      (epochs > 0, "epochs", "Experiment epochs must be positive");
      (time_limit > 0, "time_limit", "Experiment time_limit must be positive");
      ( Option.fold ~none:true ~some:(fun value -> value > 0) message_limit,
        "message_limit",
        "Experiment message_limit must be positive" );
      ( Float.is_finite cost_limit && cost_limit > 0.,
        "cost_limit",
        "Experiment cost_limit must be finite and positive" );
    ]
    { profiles; epochs; message_limit; cost_limit; time_limit; cache }

let create ~profiles ~epochs ~message_limit ~cost_limit ~time_limit ~cache =
  resolve ~profiles ~epochs ?message_limit ~cost_limit ~time_limit ~cache ()
