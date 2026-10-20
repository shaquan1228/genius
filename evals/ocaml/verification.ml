(* Outcome: observed environment result, distinct from claims in a response.
   Changed paths and verification status are this harness's observation subset.
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
   https://docs.harborframework.com/tasks/verifier *)
type t =
  | Unchecked
  | Passed
  | Failed
  | Invalid_submission
  | Timed_out
  | Harness_error of { detail : string }

let name ~status =
  match status with
  | Unchecked -> "unchecked"
  | Passed -> "passed"
  | Failed -> "failed"
  | Invalid_submission -> "invalid_submission"
  | Timed_out -> "timed_out"
  | Harness_error _ -> "harness_error"
