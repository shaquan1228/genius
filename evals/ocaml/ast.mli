(* Fixture: immutable initial files. The map implementation belongs to Fixture.
   https://inspect.aisi.org.uk/datasets.html#sample-files
   https://docs.harborframework.com/tasks/environment *)
type fixture = Fixture_store.t

(* Response: named scalar values shared by expectations and reference replies.
   https://huggingface.co/docs/lighteval/main/en/package_reference/models_outputs
   https://developers.openai.com/api/docs/guides/evals *)
type response_value = String of string | Bool of bool
type response = private { fields : (string * response_value) list }
type content = Inline of string | Resource of string

type verifier = private {
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
type instruction = private { skill : string; prompt : string }

(* Text rule: this repository's bounded-word criterion for one string field; the
   sources establish configurable success criteria, not this particular rule schema.
   https://developers.openai.com/api/docs/guides/evals
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents *)
type text_rule = private { field : string; min_words : int; max_words : int }

(* Rubric: requirements used to grade a response. Eval rubrics specify criteria;
   exact scalar expectations and a bounded-text rule are our deterministic subset.
   https://github.com/openai/evals/blob/main/docs/eval-templates.md#example-model-graded-evals
   https://teaching.cornell.edu/teaching-resources/assessing-student-learning/using-rubrics *)
type rubric = private { expected : response; text_rule : text_rule option }

(* Criterion: a declarative success condition, applied by a grader rather than by
   the candidate. The code/structured-response distinction is this repository's design.
   https://developers.openai.com/api/docs/guides/evals
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents *)
type criterion = Code of verifier | Answer of rubric

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
type task = private {
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

type experiment = private {
  profiles : profile list;
  epochs : int;
  message_limit : int option;
  cost_limit : float;
  time_limit : int;
  cache : bool;
}

type validation_code =
  | Invalid_identity
  | Invalid_path
  | Duplicate_path
  | Empty_inputs
  | Overlapping_paths
  | Invalid_command
  | Nonpositive_timeout
  | Invalid_response_field
  | Invalid_text_rule
  | Overlapping_text_field
  | Empty_answer
  | Missing_fixture_inputs
  | Artifact_overlap
  | Reference_outside_scope
  | Invalid_experiment_setting
  | Missing_resource

type validation_issue = {
  code : validation_code;
  field : string;
  message : string;
  values : string list;
}

type validation_failure = { case_id : string option; issues : validation_issue list }
type grading_failure = Verification_harness_error of string

val valid_path : string -> bool
val empty_fixture : fixture
val fixture_files : fixture -> (string * string) list
val add_fixture : path:string -> contents:string -> fixture -> (fixture, validation_failure) result
val make_fixture : (string * string) list -> (fixture, validation_failure) result
val overlay_fixture : fixture -> fixture -> fixture
val empty_response : response
val make_response : (string * response_value) list -> (response, validation_failure) result
val make_instruction : skill:string -> prompt:string -> (instruction, validation_failure) result

val make_text_rule :
  field:string -> min_words:int -> max_words:int -> (text_rule, validation_failure) result

val make_rubric :
  expected:response -> text_rule:text_rule option -> (rubric, validation_failure) result

val make_verifier :
  inputs:string list ->
  files:(string * content) list ->
  tools:(string * content) list ->
  command:string list ->
  stdin:string ->
  timeout_seconds:int ->
  (verifier, validation_failure) result

val make_task :
  id:string ->
  fixture:fixture ->
  instruction:instruction ->
  criterion:criterion ->
  allowed_files:string list ->
  reference:reference ->
  (task, validation_failure) result

val default_experiment : experiment

val make_experiment :
  ?profiles:profile list ->
  ?epochs:int ->
  ?message_limit:int ->
  ?cost_limit:float ->
  ?time_limit:int ->
  ?cache:bool ->
  unit ->
  (experiment, validation_failure) result

val resolve_resources :
  task -> resources:(string * string) list -> (task, validation_failure) result
