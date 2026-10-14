let () =
  Examples.check ~name:"both timeout defaults" Fun.id
    [ (Config.timeout_seconds, 30); (Client.fallback_timeout, 30) ];
  Examples.check ~name:"default and explicit overrides" Client.timeout
    [ (None, 30); (Some 5, 5); (Some 1, 1) ];
  Examples.rejects ~name:"nonpositive timeouts" Client.timeout [Some 0; Some (-1)]
