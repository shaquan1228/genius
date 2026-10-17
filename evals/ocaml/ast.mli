(* Shared immutable domain types. Operation signatures live in .mli files;
   constructors, validation, and evaluation live in their corresponding .ml files. *)

(* Fixture: immutable initial files. The map implementation belongs to Fixture.
   https://inspect.aisi.org.uk/datasets.html#sample-files
   https://docs.harborframework.com/tasks/environment *)
type file = private { path : string; contents : string }
type fixture = Fixture_store.t

(* Response: named scalar values shared by expectations and reference replies.
   https://huggingface.co/docs/lighteval/main/en/package_reference/models_outputs
   https://developers.openai.com/api/docs/guides/evals *)
type response_value = String of { value : string } | Bool of { value : bool }
type response_field = private { name : string; value : response_value }
type response = private { fields : response_field list }
type content = Inline of { text : string } | Resource of { key : string }
type artifact = private { path : string; content : content }
type resource_binding = private { key : string; contents : string }

type verifier = private {
  inputs : string list;
  files : artifact list;
  tools : artifact list;
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
type criterion = Code of { verifier : verifier } | Answer of { rubric : rubric }

(* Reference: reference output used for offline validation, distinct from a
   criterion's expected fields. Combining file edits and a completion is our mapping.
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
   https://evalscope.readthedocs.io/en/latest/advanced_guides/custom_dataset/llm.html *)
type completion = Plain of { text : string } | Structured of { response : response }
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
  | Harness_error of { detail : string }

type outcome = { changed_files : string list; verification : verification }

(* Score: a grader result. Named boolean correctness and scope results are this
   repository's initial representation, rather than a universal score schema.
   https://developers.openai.com/api/docs/guides/graders
   https://evalscope.readthedocs.io/en/latest/get_started/basic_usage.html *)
type score = (string * bool) list

(* Public case inputs exclude private verifier and reference material. *)
type case = private { id : string; skill : string; prompt : string; files : artifact list }
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
type grading_failure = Verification_harness_error of { detail : string }

val make_file : path:string -> contents:string -> (file, validation_failure) result
val make_artifact : path:string -> content:content -> (artifact, validation_failure) result
val make_resource_binding : key:string -> contents:string -> resource_binding
val make_fixture : files:file list -> (fixture, validation_failure) result

val make_response_field :
  name:string -> value:response_value -> (response_field, validation_failure) result

val make_response : fields:response_field list -> (response, validation_failure) result
val make_instruction : skill:string -> prompt:string -> (instruction, validation_failure) result

val make_text_rule :
  field:string -> min_words:int -> max_words:int -> (text_rule, validation_failure) result

val make_rubric :
  expected:response -> text_rule:text_rule option -> (rubric, validation_failure) result

val make_verifier :
  inputs:string list ->
  files:artifact list ->
  tools:artifact list ->
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

val empty_fixture : fixture
val fixture_files : fixture:fixture -> file list
val add_fixture : fixture:fixture -> file:file -> (fixture, validation_failure) result
val overlay_fixture : base:fixture -> overrides:fixture -> fixture
val empty_response : response
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

val project_case : task:task -> case

val resolve_resources :
  task:task -> resources:resource_binding list -> (task, validation_failure) result
