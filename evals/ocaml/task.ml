(* Task: one test specification combining instruction, initial files, a criterion, and a
   reference. Anthropic defines a task as a single test with inputs and success criteria;
   Hugging Face represents a benchmark sample with its query, expected outputs, and
   metadata. Correctness and scope are separate scores, as utility and policy compliance
   are in tau-bench and AgentDojo.
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
   https://huggingface.co/docs/lighteval/v0.13.0/package_reference/doc
   https://arxiv.org/abs/2406.13352 *)

(* Fixture files: immutable initial state, the seed for file and non-file environments.
   https://inspect.aisi.org.uk/datasets.html#sample-files
   https://docs.harborframework.com/tasks/environment *)
type file = { path : string; contents : string }

(* Instruction: the task input, mapping to lighteval's query and OpenAI eval inputs.
   https://huggingface.co/docs/lighteval/main/en/package_reference/doc *)
type instruction = { skill : string; prompt : string }

(* Verifier: an executable private check run on declared candidate inputs.
   https://docs.harborframework.com/tasks/verifier *)
type verifier = {
  inputs : string list;
  files : file list;
  tools : file list;
  command : string list;
  stdin : string;
  timeout_seconds : int;
}

(* Rubric: expected response fields and a bounded-word text rule, this repository's
   deterministic subset of a grading rubric.
   https://github.com/openai/evals/blob/main/docs/eval-templates.md#example-model-graded-evals *)
type text_rule = { field : string; min_words : int; max_words : int }
type rubric = { expected : (string * Value.t) list; text_rule : text_rule option }

(* Criterion: a declarative success condition applied by the grader: executable code, a
   rubric over the response, or a predicate over the whole observation.
   https://developers.openai.com/api/docs/guides/evals
   https://arxiv.org/abs/2406.12045 (tau-bench: final state and required outputs) *)
type criterion =
  | Code of { verifier : verifier }
  | Answer of { rubric : rubric }
  | State of { predicate : Predicate.t }

(* Reference: reference edits and completion for offline validation.
   https://evalscope.readthedocs.io/en/latest/advanced_guides/custom_dataset/llm.html *)
type reference = { edits : file list; completion : Value.t }

type t = {
  id : string;
  fixture : file list;
  instruction : instruction;
  criterion : criterion;
  allowed_files : string list;
  reference : reference;
}

(* Case: the public projection a candidate receives; private verifier and reference
   material is absent. *)
type case = { case_id : string; skill : string; prompt : string; files : file list }

let required_scores = [ "correctness"; "scope" ]
let paths ~files = List.map (fun (file : file) -> file.path) files
let checks ~task = match task.criterion with Code { verifier } -> Some verifier | _ -> None

let project ~task =
  let tools = match task.criterion with Code { verifier } -> verifier.tools | _ -> [] in
  {
    case_id = task.id;
    skill = task.instruction.skill;
    prompt = task.instruction.prompt;
    files = task.fixture @ tools;
  }

let create ~id ~fixture ~(instruction : instruction) ~criterion ~allowed_files ~reference =
  let fixture_paths = paths ~files:fixture and edits = paths ~files:reference.edits in
  let all_paths = fixture_paths @ allowed_files @ edits in
  let criterion_rules =
    match criterion with
    | Code { verifier } ->
        let artifacts = paths ~files:verifier.files @ paths ~files:verifier.tools in
        [
          (verifier.inputs <> [], "verifier.inputs", "Verifier inputs cannot be empty");
          ( List.for_all (fun input -> List.mem input fixture_paths) verifier.inputs,
            "verifier.inputs",
            "Criteria read files missing from the fixture" );
          ( not (List.exists (fun path -> List.mem path fixture_paths) artifacts),
            "verifier",
            "Verifier artifacts overlap fixture" );
          (Support.unique (verifier.inputs @ artifacts), "verifier", "Overlapping verifier paths");
          (List.for_all Support.valid_path artifacts, "verifier", "Invalid verifier path");
          ( verifier.command <> [] && not (List.mem "" verifier.command),
            "verifier.command",
            "Invalid verifier command" );
          ( verifier.timeout_seconds > 0,
            "verifier.timeout_seconds",
            "Verifier timeout must be positive" );
        ]
    | Answer { rubric } ->
        [
          (rubric.expected <> [] || rubric.text_rule <> None, "rubric", "Empty rubric");
          ( Option.fold
              ~none:true
              ~some:(fun (rule : text_rule) ->
                0 <= rule.min_words && rule.min_words <= rule.max_words
                && not (List.mem_assoc rule.field rubric.expected))
              rubric.text_rule,
            "rubric.text_rule",
            "Invalid text rule" );
        ]
    | State _ -> []
  in
  Support.checked
    ~case_id:id
    ([
       (Support.valid_name id, "id", "Invalid case identity");
       (Support.valid_name instruction.skill, "instruction.skill", "Invalid instruction skill");
       (List.for_all Support.valid_path all_paths, "fixture", "Invalid path");
       (Support.unique fixture_paths && Support.unique edits, "fixture", "Duplicate path");
       ( List.for_all (fun path -> List.mem path allowed_files) edits,
         "reference.edits",
         "Reference edits files outside allowed_files" );
     ]
    @ criterion_rules)
    { id; fixture; instruction; criterion; allowed_files; reference }

(* Every criterion is a predicate over the observation. *)
let condition ~criterion =
  match criterion with
  | Code _ ->
      Predicate.Equals { path = [ "verification" ]; expected = Value.String { value = "passed" } }
  | State { predicate } -> predicate
  | Answer { rubric } ->
      let field name = [ "response"; name ] in
      Predicate.All
        {
          checks =
            [ ("response", Predicate.Present { path = [ "response" ] }) ]
            @ List.map
                (fun (name, expected) -> (name, Predicate.Equals { path = field name; expected }))
                rubric.expected
            @ Option.to_list
                (Option.map
                   (fun (rule : text_rule) ->
                     ( "text",
                       Predicate.Words
                         {
                           path = field rule.field;
                           min_words = rule.min_words;
                           max_words = rule.max_words;
                         } ))
                   rubric.text_rule);
        }

(* Grader: pure logic applying the criterion and the file scope to an observed outcome.
   IO, execution, and presentation remain harness responsibilities.
   https://developers.openai.com/api/docs/guides/graders *)
let assess ~task ~(outcome : Outcome.t) =
  match outcome.verification with
  | Outcome.Harness_error { detail } -> Error (Failure.Verification_harness_error { detail })
  | _ ->
      let scope =
        Predicate.Within
          {
            path = [ "changed_files" ];
            allowed = List.map (fun value -> Value.String { value }) task.allowed_files;
          }
      in
      Ok
        (Assessment.create
           ~predicate:
             (Predicate.All
                {
                  checks =
                    [ ("correctness", condition ~criterion:task.criterion); ("scope", scope) ];
                })
           ~observation:(Outcome.observation ~outcome))

let grade ~task ~outcome =
  Result.map (fun assessment -> Assessment.scores ~assessment) (assess ~task ~outcome)
