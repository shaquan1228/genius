(* Instructions are data, independent of starting projects and grading policy. *)
type t = { skill : string; prompt : string }

let make ~skill ~prompt = { skill; prompt }

module Receipt = struct
  let fix_total =
    make
      ~skill:"reasoning"
      ~prompt:
        "Fix Receipt.total so each item's quantity contributes to the total. Change only \
         receipt.ml. Verify with sh check.sh receipt.ml test_receipt.ml. Complete the change and \
         summarize it."
end

module Preflight = struct
  let change_timeout ~initial ~requested =
    if initial <= 0 || requested <= 0 || initial = requested then
      invalid_arg "Timeout changes need distinct positive initial and requested values";
    make
      ~skill:"preflight"
      ~prompt:
        (Printf.sprintf
           "On branch eval, change the default timeout from %d to %d seconds in config.ml and \
            client.ml. Only those two files are in scope. Keep tests and other behavior unchanged. \
            Deliver the diff and a brief summary. Verify with sh check.sh config.ml client.ml \
            test_client.ml. Complete the change."
           initial
           requested)
end

module Decision = struct
  let cheaper ~a ~b =
    if a < 0 || b < 0 || a = b then invalid_arg "Decision needs distinct nonnegative costs";
    make
      ~skill:"bayesian"
      ~prompt:
        (Printf.sprintf
           "Choose a service for a one-month trial. A costs $%d total; B costs $%d total. \
            Features, reliability, cancellation terms, and all other costs are identical. Reply \
            with JSON containing choice (A or B) and reason (one sentence). Do not change files."
           a
           b)

  let hindsight =
    make
      ~skill:"bayesian"
      ~prompt:
        "I took a one-time $1 bet with a known 80% chance of winning $1 profit and 20% chance of \
         losing $1. I could comfortably afford the loss. I lost. No new information about the odds \
         appeared. Was the original decision supported, and should this loss alone change the \
         rule? Reply with JSON containing decision_was_supported (boolean), change_rule (boolean), \
         and reason (one sentence). Do not change files."
end
