(* Outcome: observed environment result, distinct from claims in a response.
   Changed paths and verification status are this harness's observation subset.
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
   https://docs.harborframework.com/tasks/verifier *)
type t = { changed_files : string list; verification : Verification.t }

let create ~changed_files ~verification : t = { changed_files; verification }
