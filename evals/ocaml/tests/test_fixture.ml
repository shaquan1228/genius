let rejected construct =
  assert (
    try
      ignore (construct ());
      false
    with Invalid_argument _ -> true)

let () =
  let base = Fixture.of_files [ ("config.txt", "initial") ] in
  let override = Fixture.of_files [ ("config.txt", "changed") ] in
  assert (Fixture.files base = [ ("config.txt", "initial") ]);
  assert (Fixture.files (Fixture.overlay base ~overrides:override) = [ ("config.txt", "changed") ]);
  rejected (fun () -> Fixture.of_files [ ("a", "one"); ("a", "two") ]);
  let project = Fixture.of_files [ ("source.txt", "seed"); ("visible.txt", "public check") ] in
  assert (List.mem_assoc "source.txt" (Fixture.files project));
  assert (List.length (Fixture.files project) = 2)
