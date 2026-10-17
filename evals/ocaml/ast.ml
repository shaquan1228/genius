(* Shared immutable domain types. Operation signatures live in .mli files;
   constructors, validation, and evaluation live in their corresponding .ml files. *)

(* Fixture: immutable initial files. The map implementation belongs to Fixture.
   https://inspect.aisi.org.uk/datasets.html#sample-files
   https://docs.harborframework.com/tasks/environment *)
type file = { path : string; contents : string }
type fixture = Fixture_store.t

(* Response: named scalar values shared by expectations and reference replies.
   https://huggingface.co/docs/lighteval/main/en/package_reference/models_outputs
   https://developers.openai.com/api/docs/guides/evals *)
type response_value = String of { value : string } | Bool of { value : bool }
type response_field = { name : string; value : response_value }
type response = { fields : response_field list }
type content = Inline of { text : string } | Resource of { key : string }
type artifact = { path : string; content : content }
type resource_binding = { key : string; contents : string }

type verifier = {
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
type instruction = { skill : string; prompt : string }

(* Text rule: this repository's bounded-word criterion for one string field; the
   sources establish configurable success criteria, not this particular rule schema.
   https://developers.openai.com/api/docs/guides/evals
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents *)
type text_rule = { field : string; min_words : int; max_words : int }

(* Rubric: requirements used to grade a response. Eval rubrics specify criteria;
   exact scalar expectations and a bounded-text rule are our deterministic subset.
   https://github.com/openai/evals/blob/main/docs/eval-templates.md#example-model-graded-evals
   https://teaching.cornell.edu/teaching-resources/assessing-student-learning/using-rubrics *)
type rubric = { expected : response; text_rule : text_rule option }

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
  | Harness_error of { detail : string }

type outcome = { changed_files : string list; verification : verification }

(* Score: a grader result. Named boolean correctness and scope results are this
   repository's initial representation, rather than a universal score schema.
   https://developers.openai.com/api/docs/guides/graders
   https://evalscope.readthedocs.io/en/latest/get_started/basic_usage.html *)
type score = (string * bool) list

(* Public case inputs exclude private verifier and reference material. *)
type case = { id : string; skill : string; prompt : string; files : artifact list }
type profile = { name : string; preamble : string; instructions : string list }

type experiment = {
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

let ( let* ) = Result.bind
let issue code field message values = { code; field; message; values }

let checked ?case_id issues value =
  match issues with [] -> Ok value | _ -> Error { case_id; issues }

let when_invalid condition problem = if condition then [] else [ problem ]

let valid_name name =
  name <> ""
  && (match name.[0] with 'a' .. 'z' -> true | _ -> false)
  && String.for_all (function 'a' .. 'z' | '0' .. '9' | '-' -> true | _ -> false) name

let valid_path name =
  name <> ""
  && (match name.[0] with 'a' .. 'z' | 'A' .. 'Z' | '_' -> true | _ -> false)
  && String.for_all
       (function 'a' .. 'z' | 'A' .. 'Z' | '0' .. '9' | '_' | '-' | '.' -> true | _ -> false)
       name

let path_issues field paths =
  List.filter_map
    (fun path ->
      if valid_path path then None
      else Some (issue Invalid_path field ("Invalid path: " ^ path) [ path ]))
    paths

let make_file ~path ~contents = checked (path_issues "file.path" [ path ]) { path; contents }
let make_artifact ~path ~content = checked (path_issues "artifact.path" [ path ]) { path; content }
let make_resource_binding ~key ~contents = { key; contents }
let empty_fixture = Fixture_store.empty

let fixture_files ~fixture : file list =
  List.map (fun (path, contents) -> { path; contents }) (Fixture_store.files fixture)

let add_fixture ~fixture ~(file : file) =
  checked
    (when_invalid
       (not (Fixture_store.mem file.path fixture))
       (issue Duplicate_path "fixture" ("Duplicate fixture path: " ^ file.path) [ file.path ]))
    (Fixture_store.add file.path file.contents fixture)

let make_fixture ~files =
  List.fold_left
    (fun result file ->
      let* fixture = result in
      add_fixture ~fixture ~file)
    (Ok empty_fixture)
    files

let overlay_fixture ~base ~overrides = Fixture_store.overlay base overrides
let empty_response = { fields = [] }

let make_response_field ~name ~value =
  checked
    (when_invalid
       (name <> "")
       (issue Invalid_response_field "response.name" "Response fields need nonempty names" [ name ]))
    { name; value }

let make_response ~(fields : response_field list) =
  let rec collect seen = function
    | [] -> []
    | (field : response_field) :: rest ->
        when_invalid
          (not (List.mem field.name seen))
          (issue
             Invalid_response_field
             "response.fields"
             "Response fields need unique names"
             [ field.name ])
        @ collect (field.name :: seen) rest
  in
  checked (collect [] fields) { fields }

let make_instruction ~skill ~prompt =
  checked
    (when_invalid
       (valid_name skill)
       (issue Invalid_identity "instruction.skill" "Invalid instruction skill" [ skill ]))
    { skill; prompt }

let make_text_rule ~field ~min_words ~max_words =
  checked
    (when_invalid
       (field <> "" && min_words >= 0 && max_words >= min_words)
       (issue Invalid_text_rule "text_rule" "Invalid text rule" [ field ]))
    { field; min_words; max_words }

let make_rubric ~(expected : response) ~(text_rule : text_rule option) =
  let problems =
    when_invalid
      (expected.fields <> [] || text_rule <> None)
      (issue Empty_answer "criterion" "Answer criterion cannot be empty" [])
    @
    match text_rule with
    | None -> []
    | Some rule ->
        when_invalid
          (not
             (List.exists (fun (field : response_field) -> field.name = rule.field) expected.fields))
          (issue
             Overlapping_text_field
             "text_rule.field"
             "Text rule overlaps expected fields"
             [ rule.field ])
  in
  checked problems { expected; text_rule }

let make_verifier ~inputs ~(files : artifact list) ~(tools : artifact list) ~command ~stdin
    ~timeout_seconds =
  let names = inputs @ List.map (fun (artifact : artifact) -> artifact.path) (files @ tools) in
  let problems =
    path_issues "verifier.inputs" inputs
    @ when_invalid
        (inputs <> [])
        (issue Empty_inputs "verifier.inputs" "Verifier inputs cannot be empty" [])
    @ when_invalid
        (List.length names = List.length (List.sort_uniq compare names))
        (issue Overlapping_paths "verifier" "Overlapping verifier paths" names)
    @ when_invalid
        (command <> [] && not (List.exists (( = ) "") command))
        (issue Invalid_command "verifier.command" "Invalid verifier command" command)
    @ when_invalid
        (timeout_seconds > 0)
        (issue
           Nonpositive_timeout
           "verifier.timeout_seconds"
           "Verifier timeout must be positive"
           [])
  in
  checked problems { inputs; files; tools; command; stdin; timeout_seconds }

let make_task ~id ~fixture ~(instruction : instruction) ~criterion ~allowed_files
    ~(reference : reference) =
  let paths fixture = List.map (fun (file : file) -> file.path) (fixture_files ~fixture) in
  let require code field problem ~within names =
    let missing = List.filter (fun name -> not (List.mem name within)) names in
    when_invalid
      (missing = [])
      (issue
         code
         field
         (Printf.sprintf "Case %s: %s: %s" id problem (String.concat ", " missing))
         missing)
  in
  let problems =
    when_invalid (valid_name id) (issue Invalid_identity "id" "Invalid case identity" [ id ])
    @ path_issues "allowed_files" allowed_files
    @ require
        Reference_outside_scope
        "reference.edits"
        "reference edits files outside allowed_files"
        ~within:allowed_files
        (paths reference.edits)
    @
    match criterion with
    | Answer _ -> []
    | Code { verifier } ->
        require
          Missing_fixture_inputs
          "verifier.inputs"
          "criteria read files missing from the fixture"
          ~within:(paths fixture)
          verifier.inputs
        @ when_invalid
            (not
               (List.exists
                  (fun (artifact : artifact) -> List.mem artifact.path (paths fixture))
                  (verifier.files @ verifier.tools)))
            (issue
               Artifact_overlap
               "verifier"
               ("Case " ^ id ^ ": verifier artifacts overlap fixture")
               [])
  in
  checked ~case_id:id problems { id; fixture; instruction; criterion; allowed_files; reference }

let default_experiment =
  {
    profiles =
      [
        { name = "baseline"; preamble = ""; instructions = [] };
        {
          name = "genius";
          preamble =
            "Read ../instructions/skills/{skill}/SKILL.md and its referenced files. Apply that \
             skill to this task.\n\n";
          instructions = [ "docs"; "skills" ];
        };
      ];
    epochs = 5;
    message_limit = None;
    cost_limit = 0.25;
    time_limit = 300;
    cache = false;
  }

let make_experiment ?(profiles = default_experiment.profiles) ?(epochs = default_experiment.epochs)
    ?message_limit ?(cost_limit = default_experiment.cost_limit)
    ?(time_limit = default_experiment.time_limit) ?(cache = default_experiment.cache) () =
  let positive field value =
    when_invalid
      (value > 0)
      (issue Invalid_experiment_setting field ("Experiment " ^ field ^ " must be positive") [])
  in
  let problems =
    positive "epochs" epochs @ positive "time_limit" time_limit
    @ (match message_limit with None -> [] | Some value -> positive "message_limit" value)
    @ when_invalid
        (Float.is_finite cost_limit && cost_limit > 0.)
        (issue
           Invalid_experiment_setting
           "cost_limit"
           "Experiment cost_limit must be finite and positive"
           [])
  in
  checked problems { profiles; epochs; message_limit; cost_limit; time_limit; cache }

let project_case ~(task : task) : case =
  let tools = match task.criterion with Code { verifier } -> verifier.tools | Answer _ -> [] in
  {
    id = task.id;
    skill = task.instruction.skill;
    prompt = task.instruction.prompt;
    files =
      List.map
        (fun (file : file) -> { path = file.path; content = Inline { text = file.contents } })
        (fixture_files ~fixture:task.fixture)
      @ tools;
  }

let resolve_resources ~(task : task) ~(resources : resource_binding list) =
  let resolve (artifact : artifact) =
    match artifact.content with
    | Inline _ -> Ok artifact
    | Resource { key } -> (
        match List.find_opt (fun (binding : resource_binding) -> binding.key = key) resources with
        | Some binding -> Ok { artifact with content = Inline { text = binding.contents } }
        | None ->
            Error
              {
                case_id = Some task.id;
                issues =
                  [ issue Missing_resource artifact.path ("Missing resource: " ^ key) [ key ] ];
              })
  in
  let rec resolve_all = function
    | [] -> Ok []
    | value :: rest ->
        let* value = resolve value in
        let* rest = resolve_all rest in
        Ok (value :: rest)
  in
  match task.criterion with
  | Answer _ -> Ok task
  | Code { verifier } ->
      let* files = resolve_all verifier.files in
      let* tools = resolve_all verifier.tools in
      Ok { task with criterion = Code { verifier = { verifier with files; tools } } }
