(* Failures: a rejected declaration keeps every issue; a grading failure is a harness
   fault, kept apart from an incorrect candidate.
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents *)
type issue = { field : string; message : string }
type validation_failure = { case_id : string option; issues : issue list }
type grading_failure = Verification_harness_error of { detail : string }
