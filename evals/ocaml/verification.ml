type t =
  | Unchecked
  | Passed
  | Failed
  | Invalid_submission
  | Timed_out
  | Harness_error of { detail : string }
