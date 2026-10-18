type t = {
  inputs : string list;
  files : Artifact.t list;
  tools : Artifact.t list;
  command : string list;
  stdin : string;
  timeout_seconds : int;
}

let create ~inputs ~(files : Artifact.t list) ~(tools : Artifact.t list) ~command ~stdin
    ~timeout_seconds =
  let names = inputs @ List.map (fun (artifact : Artifact.t) -> artifact.path) (files @ tools) in
  let problems =
    File.path_issues ~field:"verifier.inputs" ~paths:inputs
    @ Validation.when_invalid
        (inputs <> [])
        (Validation.issue
           Validation_code.Empty_inputs
           "verifier.inputs"
           "Verifier inputs cannot be empty"
           [])
    @ Validation.when_invalid
        (List.length names = List.length (List.sort_uniq compare names))
        (Validation.issue
           Validation_code.Overlapping_paths
           "verifier"
           "Overlapping verifier paths"
           names)
    @ Validation.when_invalid
        (command <> [] && not (List.exists (( = ) "") command))
        (Validation.issue
           Validation_code.Invalid_command
           "verifier.command"
           "Invalid verifier command"
           command)
    @ Validation.when_invalid
        (timeout_seconds > 0)
        (Validation.issue
           Validation_code.Nonpositive_timeout
           "verifier.timeout_seconds"
           "Verifier timeout must be positive"
           [])
  in
  Validation.checked problems { inputs; files; tools; command; stdin; timeout_seconds }

let resolve_resources ~(verifier : t) ~resources =
  let rec resolve_all = function
    | [] -> Ok []
    | artifact :: rest ->
        Result.bind (Artifact.resolve ~artifact ~resources) (fun artifact ->
            Result.map (fun rest -> artifact :: rest) (resolve_all rest))
  in
  Result.bind (resolve_all verifier.files) (fun files ->
      Result.map (fun tools -> { verifier with files; tools }) (resolve_all verifier.tools))

let compare ~(before : t) ~(after : t) =
  Comparison.create
    ~fields:
      [
        ( "inputs",
          List.sort_uniq String.compare before.inputs = List.sort_uniq String.compare after.inputs
        );
        ("files", List.sort Stdlib.compare before.files = List.sort Stdlib.compare after.files);
        ("tools", List.sort Stdlib.compare before.tools = List.sort Stdlib.compare after.tools);
        ("command", before.command = after.command);
        ("stdin", before.stdin = after.stdin);
        ("timeout_seconds", before.timeout_seconds = after.timeout_seconds);
      ]
