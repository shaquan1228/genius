type verification =
  | Unchecked
  | Passed
  | Failed
  | Invalid_submission
  | Timed_out
  | Harness_error of string

type t = { changed_files : string list; verification : verification }

let make ~changed_files ~verification = { changed_files; verification }
