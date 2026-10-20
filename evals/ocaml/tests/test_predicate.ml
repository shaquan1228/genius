let s value = Value.String { value }
let i value = Value.Int { value }
let r fields = Value.Record { fields }
let call = r [ ("name", s "lookup"); ("arguments", r [ ("id", i 7) ]) ]

let observation =
  r
    [
      ("response", r [ ("choice", s "B"); ("reason", s "one two three") ]);
      ("trace", Value.List { items = [ call ] });
      ("state", r [ ("balance", i 5); ("note", Value.Null) ]);
    ]

let () =
  assert (Value.get ~value:observation ~path:[ "state"; "balance" ] = Some (i 5));
  assert (Value.get ~value:observation ~path:[ "state"; "missing" ] = None);
  assert (Value.get ~value:observation ~path:[ "response"; "choice"; "deeper" ] = None);
  assert (Value.get ~value:observation ~path:[] = Some observation);
  assert (Value.equal ~left:(r [ ("a", i 1); ("b", i 2) ]) ~right:(r [ ("b", i 2); ("a", i 1) ]));
  assert (Value.equal ~left:(r [ ("a", i 1); ("a", i 2) ]) ~right:(r [ ("a", i 1) ]));
  assert (not (Value.equal ~left:(r [ ("a", i 1) ]) ~right:(r [ ("a", i 1); ("b", i 2) ])));
  assert (
    not
      (Value.equal
         ~left:(Value.strings ~values:[ "a"; "b" ])
         ~right:(Value.strings ~values:[ "b"; "a" ])));
  assert (not (Value.equal ~left:(i 1) ~right:(Value.Float { value = 1.0 })));
  assert (Value.equal ~left:Value.Null ~right:Value.Null)

let () =
  let check predicate = Predicate.holds ~predicate ~observation in
  let open Predicate in
  assert (check (Present { path = [ "state"; "balance" ] }));
  assert (not (check (Present { path = [ "state"; "note" ] })));
  assert (not (check (Present { path = [ "absent" ] })));
  assert (check (Equals { path = [ "response"; "choice" ]; expected = s "B" }));
  assert (not (check (Equals { path = [ "response"; "choice" ]; expected = s "A" })));
  assert (not (check (Equals { path = [ "absent" ]; expected = Value.Null })));
  assert (check (Contains { path = [ "trace" ]; item = call }));
  assert (not (check (Contains { path = [ "trace" ]; item = s "lookup" })));
  assert (not (check (Contains { path = [ "state" ]; item = call })));
  assert (check (Within { path = [ "trace" ]; allowed = [ call ] }));
  assert (not (check (Within { path = [ "trace" ]; allowed = [] })));
  assert (not (check (Within { path = [ "response" ]; allowed = [ call ] })));
  assert (check (Words { path = [ "response"; "reason" ]; min_words = 3; max_words = 3 }));
  assert (not (check (Words { path = [ "response"; "reason" ]; min_words = 4; max_words = 9 })));
  assert (not (check (Words { path = [ "state"; "balance" ]; min_words = 0; max_words = 9 })));
  let yes = Present { path = [ "state" ] } and no = Present { path = [ "absent" ] } in
  assert (check (All { checks = [] }));
  assert (not (check (Any { checks = [] })));
  assert (not (check (All { checks = [ ("yes", yes); ("no", no) ] })));
  assert (check (Any { checks = [ ("yes", yes); ("no", no) ] }));
  assert (check (Not { check = no }));
  assert (not (check (Not { check = yes })))

let utf8 code =
  let buffer = Buffer.create 4 in
  Buffer.add_utf_8_uchar buffer (Uchar.of_int code);
  Buffer.contents buffer

let () =
  let separators =
    List.init 5 (( + ) 9)
    @ List.init 5 (( + ) 28)
    @ [ 133; 160; 5760 ]
    @ List.init 11 (( + ) 8192)
    @ [ 8232; 8233; 8239; 8287; 12288 ]
  in
  List.iter
    (fun code -> assert (Support.word_count ("first" ^ utf8 code ^ "second") = 2))
    separators;
  assert (Support.word_count ("first" ^ utf8 0x200B ^ "second") = 1);
  assert (Support.word_count "" = 0);
  assert (Support.word_count "  one  " = 1)
