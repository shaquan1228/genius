(* Outcome: observed environment result, distinct from claims in a response.
   Changed paths and verification status are this harness's file-level observation;
   open facts carry whatever else the harness observed, such as a tool trace or
   environment state, so non-file environments need no new kernel types.
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
   https://docs.harborframework.com/tasks/verifier
   https://arxiv.org/abs/2506.07982 (tau2-bench: state, actions, and messages per episode) *)
type t = {
  changed_files : string list;
  verification : Verification.t;
  facts : (string * Value.t) list;
}

val create :
  ?facts:(string * Value.t) list ->
  changed_files:string list ->
  verification:Verification.t ->
  unit ->
  t

val observation : outcome:t -> response:Response.t option -> Value.t
(** One record over every observed channel: [changed_files], [verification], [response], then the
    open facts. *)
