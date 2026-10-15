type profile = { name : string; preamble : string; instructions : string list }

type t = {
  profiles : profile list;
  epochs : int;
  message_limit : int;
  token_limit : int;
  time_limit : int;
  cache : bool;
}

let default =
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
