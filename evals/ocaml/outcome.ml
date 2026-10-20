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

let create ?(facts = []) ~changed_files ~verification () : t =
  { changed_files; verification; facts }

let observation ~outcome ~response =
  Value.Record
    {
      fields =
        [
          ("changed_files", Value.strings ~values:outcome.changed_files);
          ("verification", Value.String { value = Verification.name ~status:outcome.verification });
          ( "response",
            Option.fold ~none:Value.Null ~some:(fun response -> Response.value ~response) response
          );
        ]
        @ outcome.facts;
    }
