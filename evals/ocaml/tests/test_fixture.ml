let rejected construct =
  assert (
    try
      ignore (construct ());
      false
    with Invalid_argument _ -> true)

let () =
  let base = Fixture.of_files [ ("config.ml", "initial") ] in
  let override = Fixture.of_files [ ("config.ml", "changed") ] in
  assert (Fixture.files base = [ ("config.ml", "initial") ]);
  assert (Fixture.files (Fixture.overlay base ~overrides:override) = [ ("config.ml", "changed") ]);
  rejected (fun () -> Fixture.of_files [ ("a", "one"); ("a", "two") ]);
  let project = Fixtures.Receipt.fixture ~bug:Ignore_quantity in
  assert (List.mem_assoc "receipt.ml" (Fixture.files project));
  assert (List.length (Fixture.files project) = 2)
