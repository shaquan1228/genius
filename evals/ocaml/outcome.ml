(* Outcome: observed environment result, distinct from claims in a response.
   Changed paths and trusted code execution status are this harness's observation subset.
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
   https://docs.harborframework.com/tasks/verifier *)
type t = { changed_files : string list; code_passed : bool }

let make ~changed_files ~code_passed = { changed_files; code_passed }
