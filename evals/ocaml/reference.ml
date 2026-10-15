(* Known edits and replies used only by the offline scripted test agent. *)
type t = Edits of Fixture.t | Reply of { answer : Check.answer; reason : string }

let edits files = Edits files
let reply ~answer ~reason = Reply { answer; reason }

let receipt =
  edits
    (Fixture.of_files
       [
         ( "receipt.ml",
           {|let total items =
  List.fold_left (fun sum (price, quantity) -> sum +. price *. float_of_int quantity) 0. items
|}
         );
       ])

let preflight ~timeout =
  edits
    (Fixture.of_files
       [
         ("config.ml", Fixtures.Preflight.config timeout);
         ("client.ml", Fixtures.Preflight.client timeout);
       ])
