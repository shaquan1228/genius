let fixture files = Result.get_ok (Fixture.of_files files)

let () =
  let base = fixture [ ("config.txt", "initial") ] in
  let override = fixture [ ("config.txt", "changed") ] in
  assert (Fixture.files base = [ ("config.txt", "initial") ]);
  assert (Fixture.files (Fixture.overlay base ~overrides:override) = [ ("config.txt", "changed") ]);
  assert (Result.is_error (Fixture.of_files [ ("a", "one"); ("a", "two") ]));
  assert (Result.is_error (Fixture.of_files [ ("../bad", "contents") ]));
  let project = fixture [ ("source.txt", "seed"); ("visible.txt", "public check") ] in
  assert (List.mem_assoc "source.txt" (Fixture.files project));
  assert (List.length (Fixture.files project) = 2)
