(* Shared immutable domain types. Operation signatures live in .mli files;
   constructors, validation, and evaluation live in their corresponding .ml files. *)

(* Fixture: immutable initial files. The map implementation belongs to Fixture.
   https://inspect.aisi.org.uk/datasets.html#sample-files
   https://docs.harborframework.com/tasks/environment *)
type fixture = string Map.Make(String).t

(* Response: named scalar values shared by expectations and reference replies.
   https://huggingface.co/docs/lighteval/main/en/package_reference/models_outputs
   https://developers.openai.com/api/docs/guides/evals *)
type response_value = String of string | Bool of bool
type response = (string * response_value) list
type content = Inline of string | Resource of string

type verifier = {
  inputs : string list;
  files : (string * content) list;
  tools : (string * content) list;
  command : string list;
  stdin : string;
  timeout_seconds : int;
}

(* Instruction: task input describing the requested behavior. This prompt-only value
   maps to Hugging Face's instruction/query and OpenAI eval inputs.
   https://huggingface.co/docs/lighteval/main/en/package_reference/doc
   https://developers.openai.com/api/docs/guides/evals *)
type instruction = { skill : string; prompt : string }

(* Text rule: this repository's bounded-word criterion for one string field; the
   sources establish configurable success criteria, not this particular rule schema.
   https://developers.openai.com/api/docs/guides/evals
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents *)
type text_rule = { field : string; min_words : int; max_words : int }

(* Criterion: a declarative success condition, applied by a grader rather than by
   the candidate. The code/structured-response distinction is this repository's design.
   https://developers.openai.com/api/docs/guides/evals
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents *)
type answer = { expected : response; text_rule : text_rule option }
type criterion = Code of verifier | Answer of answer

(* Reference: reference output used for offline validation, distinct from a
   criterion's expected fields. Combining file edits and a completion is our mapping.
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
   https://evalscope.readthedocs.io/en/latest/advanced_guides/custom_dataset/llm.html *)
type completion = Plain of string | Structured of response
type reference = { edits : fixture; completion : completion }

(* Task: one test specification combining instruction, initial state, criteria, and reference.
   Anthropic defines a task as a single test with inputs and success criteria; Hugging Face
   represents a benchmark sample with its query, expected outputs, and task metadata.
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
   https://huggingface.co/docs/lighteval/v0.13.0/package_reference/doc *)
type task = {
  id : string;
  fixture : fixture;
  instruction : instruction;
  criterion : criterion;
  allowed_files : string list;
  reference : reference;
}

(* Outcome: observed environment result, distinct from claims in a response.
   Changed paths and verification status are this harness's observation subset.
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
   https://docs.harborframework.com/tasks/verifier *)
type verification =
  | Unchecked
  | Passed
  | Failed
  | Invalid_submission
  | Timed_out
  | Harness_error of string

type outcome = { changed_files : string list; verification : verification }

(* Score: a grader result. Named boolean correctness and scope results are this
   repository's initial representation, rather than a universal score schema.
   https://developers.openai.com/api/docs/guides/graders
   https://evalscope.readthedocs.io/en/latest/get_started/basic_usage.html *)
type score = (string * bool) list

(* Public case inputs exclude private verifier and reference material. *)
type case = { id : string; skill : string; prompt : string; files : (string * content) list }
type profile = { name : string; preamble : string; instructions : string list }

type experiment = {
  profiles : profile list;
  epochs : int;
  message_limit : int option;
  cost_limit : float;
  time_limit : int;
  cache : bool;
}
