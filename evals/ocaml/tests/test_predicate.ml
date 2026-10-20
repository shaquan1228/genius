let string value = Value.String { value }
let int value = Value.Int { value }
let record fields = Value.Record { fields }
let ok result = Result.get_ok result

let observation =
  record
    [
      ("response", record [ ("choice", string "B"); ("reason", string "one two three") ]);
      ( "trace",
        Value.List
          {
            items =
              [ record [ ("name", string "lookup"); ("arguments", record [ ("id", int 7) ]) ] ];
          } );
      ("state", record [ ("balance", int 5); ("note", Value.Null) ]);
    ]

let () =
  assert (Value.get ~value:observation ~path:[ "state"; "balance" ] = Some (int 5));
  assert (Value.get ~value:observation ~path:[ "state"; "missing" ] = None);
  assert (Value.get ~value:observation ~path:[ "response"; "choice"; "deeper" ] = None);
  assert (Value.get ~value:observation ~path:[] = Some observation);
  assert (
    Value.equal
      ~left:(record [ ("a", int 1); ("b", int 2) ])
      ~right:(record [ ("b", int 2); ("a", int 1) ]));
  assert (Value.equal ~left:(record [ ("a", int 1); ("a", int 2) ]) ~right:(record [ ("a", int 1) ]));
  assert (
    not
      (Value.equal
         ~left:(Value.strings ~values:[ "a"; "b" ])
         ~right:(Value.strings ~values:[ "b"; "a" ])));
  assert (not (Value.equal ~left:(int 1) ~right:(Value.Float { value = 1.0 })));
  assert (Value.equal ~left:Value.Null ~right:Value.Null)

let () =
  let holds predicate = Predicate.holds ~predicate ~observation in
  assert (holds (ok (Predicate.present ~path:[ "state"; "balance" ])));
  assert (not (holds (ok (Predicate.present ~path:[ "state"; "note" ]))));
  assert (not (holds (ok (Predicate.present ~path:[ "absent" ]))));
  assert (holds (ok (Predicate.equals ~path:[ "response"; "choice" ] ~expected:(string "B"))));
  assert (not (holds (ok (Predicate.equals ~path:[ "response"; "choice" ] ~expected:(string "A")))));
  assert (not (holds (ok (Predicate.equals ~path:[ "absent" ] ~expected:Value.Null))));
  let call = record [ ("name", string "lookup"); ("arguments", record [ ("id", int 7) ]) ] in
  assert (holds (ok (Predicate.contains ~path:[ "trace" ] ~item:call)));
  assert (not (holds (ok (Predicate.contains ~path:[ "trace" ] ~item:(string "lookup")))));
  assert (not (holds (ok (Predicate.contains ~path:[ "state" ] ~item:call))));
  assert (holds (ok (Predicate.within ~path:[ "trace" ] ~allowed:[ call ])));
  assert (not (holds (ok (Predicate.within ~path:[ "trace" ] ~allowed:[]))));
  assert (not (holds (ok (Predicate.within ~path:[ "response" ] ~allowed:[ call ]))));
  assert (holds (ok (Predicate.within ~path:[ "empty" ] ~allowed:[])) = false);
  assert (holds (ok (Predicate.words ~path:[ "response"; "reason" ] ~min_words:3 ~max_words:3)));
  assert (
    not (holds (ok (Predicate.words ~path:[ "response"; "reason" ] ~min_words:4 ~max_words:9))));
  assert (not (holds (ok (Predicate.words ~path:[ "state"; "balance" ] ~min_words:0 ~max_words:9))));
  let yes = ok (Predicate.present ~path:[ "state" ])
  and no = ok (Predicate.present ~path:[ "absent" ]) in
  assert (holds (ok (Predicate.all ~checks:[])));
  assert (not (holds (ok (Predicate.any ~checks:[]))));
  assert (not (holds (ok (Predicate.all ~checks:[ ("yes", yes); ("no", no) ]))));
  assert (holds (ok (Predicate.any ~checks:[ ("yes", yes); ("no", no) ])));
  assert (holds (Predicate.not_ ~check:no));
  assert (not (holds (Predicate.not_ ~check:yes)));
  assert (Predicate.compare ~before:yes ~after:yes).equal;
  assert ((Predicate.compare ~before:yes ~after:no).changed_fields = [ "predicate" ])

let codes = function
  | Ok _ -> assert false
  | Error failure ->
      List.map (fun (issue : Validation_issue.t) -> issue.code) failure.Validation_failure.issues

let () =
  assert (codes (Predicate.present ~path:[]) = [ Validation_code.Invalid_predicate ]);
  assert (
    codes (Predicate.equals ~path:[ "a"; "" ] ~expected:Value.Null)
    = [ Validation_code.Invalid_predicate ]);
  assert (codes (Predicate.within ~path:[ "" ] ~allowed:[]) = [ Validation_code.Invalid_predicate ]);
  assert (
    codes (Predicate.contains ~path:[] ~item:Value.Null) = [ Validation_code.Invalid_predicate ]);
  assert (
    codes (Predicate.words ~path:[ "a" ] ~min_words:(-1) ~max_words:1)
    = [ Validation_code.Invalid_predicate ]);
  assert (
    codes (Predicate.words ~path:[ "a" ] ~min_words:2 ~max_words:1)
    = [ Validation_code.Invalid_predicate ]);
  assert (
    codes (Predicate.words ~path:[] ~min_words:2 ~max_words:1)
    = [ Validation_code.Invalid_predicate; Validation_code.Invalid_predicate ]);
  let yes = ok (Predicate.present ~path:[ "state" ]) in
  assert (
    codes (Predicate.all ~checks:[ ("same", yes); ("same", yes) ])
    = [ Validation_code.Invalid_identity ]);
  assert (codes (Predicate.any ~checks:[ ("", yes) ]) = [ Validation_code.Invalid_identity ])
