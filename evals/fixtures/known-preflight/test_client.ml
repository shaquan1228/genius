let () =
  Examples.check ~name:"default and override" Client.timeout
    [ (None, Config.timeout_seconds); (Some 5, 5) ];
  Examples.rejects ~name:"invalid timeout" Client.timeout [Some 0]
