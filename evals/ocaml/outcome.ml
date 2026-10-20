(* Outcome: what the harness observed, distinct from claims in a response. The
   verification status stays typed so a harness fault is never an incorrect candidate;
   open facts carry a tool trace, environment state, or anything else observed.
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
   https://docs.harborframework.com/tasks/verifier
   https://arxiv.org/abs/2506.07982 (tau2-bench: state, actions, and messages per episode) *)
type verification =
  | Unchecked
  | Passed
  | Failed
  | Invalid_submission
  | Timed_out
  | Harness_error of { detail : string }

type t = {
  changed_files : string list;
  verification : verification;
  response : Value.t;
  facts : (string * Value.t) list;
}

let status ~verification =
  match verification with
  | Unchecked -> "unchecked"
  | Passed -> "passed"
  | Failed -> "failed"
  | Invalid_submission -> "invalid_submission"
  | Timed_out -> "timed_out"
  | Harness_error _ -> "harness_error"

let create ?(response = Value.Null) ?(facts = []) ~changed_files ~verification () : t =
  { changed_files; verification; response; facts }

(* One record over every observed channel; predicates address channels by path. *)
let observation ~outcome =
  Value.Record
    {
      fields =
        [
          ("changed_files", Value.strings ~values:outcome.changed_files);
          ("verification", Value.String { value = status ~verification:outcome.verification });
          ("response", outcome.response);
        ]
        @ outcome.facts;
    }
