let file ~path ~contents = Result.get_ok (File.create ~path ~contents)
let fixture ~files = Result.get_ok (Fixture.create ~files)

let () =
  let initial = file ~path:"config.txt" ~contents:"initial" in
  let replacement = file ~path:"config.txt" ~contents:"changed" in
  let base = fixture ~files:[ initial ] in
  let overrides = fixture ~files:[ replacement ] in
  assert (Fixture.files ~fixture:base = [ initial ]);
  assert (Fixture.files ~fixture:(Fixture.overlay ~base ~overrides) = [ replacement ]);
  assert (Result.is_error (Fixture.create ~files:[ initial; replacement ]));
  assert (Result.is_error (File.create ~path:"../bad" ~contents:"contents"));
  let project =
    fixture
      ~files:
        [
          file ~path:"source.txt" ~contents:"seed";
          file ~path:"visible.txt" ~contents:"public check";
        ]
  in
  assert (List.length (Fixture.files ~fixture:project) = 2)
