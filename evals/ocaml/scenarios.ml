(* Suite-specific instructions, criteria, and reference outputs. *)
module Receipt = struct
  let fix_total =
    Instruction.make
      ~skill:"reasoning"
      ~prompt:
        "Fix Receipt.total so each item's quantity contributes to the total. Change only \
         receipt.ml. Verify with sh check.sh receipt.ml test_receipt.ml. Complete the change and \
         summarize it."

  type item = { price : float; quantity : int }
  type example = { items : item list; total : float }

  let item ~price ~quantity = { price; quantity }
  let expect ~items ~total = { items; total }

  let number value =
    if not (Float.is_finite value) then invalid_arg "Receipt examples must be finite";
    Float.to_string value

  let assertion { items; total } =
    let literal { price; quantity } = Printf.sprintf "(%s, %d)" (number price) quantity in
    let items = String.concat "; " (List.map literal items) in
    Printf.sprintf "Receipt.total [%s] = %s" items (number total)

  let totals examples =
    Criterion.ocaml ~sources:[ "receipt.ml" ] ~assertions:(List.map assertion examples)

  let reference =
    Reference.edits
      (Fixture.of_files
         [
           ( "receipt.ml",
             {|let total items =
  List.fold_left (fun sum (price, quantity) -> sum +. price *. float_of_int quantity) 0. items
|}
           );
         ])
end

module Preflight = struct
  let change_timeout ~initial ~requested =
    if initial <= 0 || requested <= 0 || initial = requested then
      invalid_arg "Timeout changes need distinct positive initial and requested values";
    Instruction.make
      ~skill:"preflight"
      ~prompt:
        (Printf.sprintf
           "On branch eval, change the default timeout from %d to %d seconds in config.ml and \
            client.ml. Only those two files are in scope. Keep tests and other behavior unchanged. \
            Deliver the diff and a brief summary. Verify with sh check.sh config.ml client.ml \
            test_client.ml. Complete the change."
           initial
           requested)

  let defaults ~timeout =
    Criterion.ocaml
      ~sources:[ "config.ml"; "client.ml" ]
      ~assertions:
        [
          Printf.sprintf "Config.timeout_seconds = %d" timeout;
          Printf.sprintf "Client.fallback_timeout = %d" timeout;
          Printf.sprintf "Client.timeout None = %d" timeout;
          "Client.timeout (Some 5) = 5";
          "Client.timeout (Some 1) = 1";
          "try ignore (Client.timeout (Some 0)); false with Invalid_argument _ -> true";
          "try ignore (Client.timeout (Some (-1))); false with Invalid_argument _ -> true";
        ]

  let reference ~timeout =
    Reference.edits
      (Fixture.of_files
         [
           ("config.ml", Fixtures.Preflight.config timeout);
           ("client.ml", Fixtures.Preflight.client timeout);
         ])
end

module Decision = struct
  type choice = A | B

  let cheaper ~a ~b =
    if a < 0 || b < 0 || a = b then invalid_arg "Decision needs distinct nonnegative costs";
    Instruction.make
      ~skill:"bayesian"
      ~prompt:
        (Printf.sprintf
           "Choose a service for a one-month trial. A costs $%d total; B costs $%d total. \
            Features, reliability, cancellation terms, and all other costs are identical. Reply \
            with JSON containing choice (A or B) and reason (one sentence). Do not change files."
           a
           b)

  let hindsight =
    Instruction.make
      ~skill:"bayesian"
      ~prompt:
        "I took a one-time $1 bet with a known 80% chance of winning $1 profit and 20% chance of \
         losing $1. I could comfortably afford the loss. I lost. No new information about the odds \
         appeared. Was the original decision supported, and should this loss alone change the \
         rule? Reply with JSON containing decision_was_supported (boolean), change_rule (boolean), \
         and reason (one sentence). Do not change files."

  let reason_rule = Criterion.text_rule ~field:"reason" ~min_words:1 ~max_words:40

  let choice_fields choice =
    [ ("choice", Response.String (match choice with A -> "A" | B -> "B")) ]

  let review_fields ~supported ~change_rule =
    [
      ("decision_was_supported", Response.Bool supported); ("change_rule", Response.Bool change_rule);
    ]

  let criterion fields =
    Criterion.answer ~text_rule:reason_rule ~expected:(Response.of_fields fields) ()

  let choice expected = criterion (choice_fields expected)
  let review ~supported ~change_rule = criterion (review_fields ~supported ~change_rule)

  let reply fields ~reason =
    Reference.make
      (Structured (Response.of_fields (fields @ [ ("reason", Response.String reason) ])))

  let choice_reference expected ~reason = reply (choice_fields expected) ~reason

  let review_reference ~supported ~change_rule ~reason =
    reply (review_fields ~supported ~change_rule) ~reason
end
