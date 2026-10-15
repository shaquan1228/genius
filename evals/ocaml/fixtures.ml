(* Starting projects only: no task policy, expected outcomes, or export protocol. *)
module Receipt = struct
  type bug = Ignore_quantity | Clamp_quantity

  let fixture ~bug =
    let term =
      match bug with
      | Ignore_quantity -> "price"
      | Clamp_quantity -> "price *. float_of_int (max quantity 1)"
    in
    Fixture.of_files
      [
        ( "receipt.ml",
          Printf.sprintf
            "let total items =\n\
            \  List.fold_left (fun sum (price, quantity) -> sum +. %s) 0. items\n"
            term );
        ( "test_receipt.ml",
          {|let () =
  assert (Receipt.total [] = 0.);
  assert (Receipt.total [(3., 1); (4., 1)] = 7.)
|}
        );
      ]
end

module Preflight = struct
  let config timeout = Printf.sprintf "let timeout_seconds = %d\n" timeout

  let client timeout =
    Printf.sprintf
      {|let fallback_timeout = %d

let timeout = function
  | None -> fallback_timeout
  | Some value ->
      if value <= 0 then invalid_arg "timeout must be positive";
      value
|}
      timeout

  let fixture ~timeout =
    Fixture.of_files
      [
        ("config.ml", config timeout);
        ("client.ml", client timeout);
        ( "test_client.ml",
          {|let () =
  assert (Client.timeout None = Config.timeout_seconds);
  assert (Client.timeout (Some 5) = 5);
  assert (try ignore (Client.timeout (Some 0)); false with Invalid_argument _ -> true)
|}
        );
      ]
end
