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
  let positive field value =
    Validation.when_invalid
      (value > 0)
      (Validation.issue
         Validation_code.Invalid_experiment_setting
         field
         ("Experiment " ^ field ^ " must be positive")
         [])
  in
  let problems =
    positive "epochs" epochs @ positive "time_limit" time_limit
    @ (match message_limit with None -> [] | Some value -> positive "message_limit" value)
    @ Validation.when_invalid
        (Float.is_finite cost_limit && cost_limit > 0.)
        (Validation.issue
           Validation_code.Invalid_experiment_setting
           "cost_limit"
           "Experiment cost_limit must be finite and positive"
           [])
  in
  Validation.checked problems { profiles; epochs; message_limit; cost_limit; time_limit; cache }

let create ~profiles ~epochs ~message_limit ~cost_limit ~time_limit ~cache =
  resolve ~profiles ~epochs ?message_limit ~cost_limit ~time_limit ~cache ()
