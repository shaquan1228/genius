(* Task: one test specification combining instruction, initial state, criteria, and reference.
   Anthropic defines a task as a single test with inputs and success criteria; Hugging Face
   represents a benchmark sample with its query, expected outputs, and task metadata.
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
   https://huggingface.co/docs/lighteval/v0.13.0/package_reference/doc *)
module Comparison : sig
  type t = private {
    equal : bool;
    id : Comparison.t;
    fixture : Fixture_comparison.t;
    instruction : Comparison.t;
    criterion : Comparison.t;
    allowed_files : Comparison.t;
    reference : Comparison.t;
  }

  val create :
    id:Comparison.t ->
    fixture:Fixture_comparison.t ->
    instruction:Comparison.t ->
    criterion:Comparison.t ->
    allowed_files:Comparison.t ->
    reference:Comparison.t ->
    t
end

type t = private {
  id : string;
  fixture : Fixture.t;
  instruction : Instruction.t;
  criterion : Criterion.t;
  allowed_files : string list;
  reference : Reference.t;
}

val create :
  id:string ->
  fixture:Fixture.t ->
  instruction:Instruction.t ->
  criterion:Criterion.t ->
  allowed_files:string list ->
  reference:Reference.t ->
  (t, Validation_failure.t) result

val resolve_resources :
  task:t -> resources:Resource_binding.t list -> (t, Validation_failure.t) result

val required_scores : string list

(* Grader: pure logic applying criteria to responses and observed outcomes.
   IO, execution, and presentation remain harness responsibilities.
   https://developers.openai.com/api/docs/guides/graders
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents *)
val grade :
  task:t -> response:Response.t option -> outcome:Outcome.t -> (Score.t, Grading_failure.t) result

val verifier : task:t -> Verifier.t option
val compare : before:t -> after:t -> Comparison.t

val assess :
  task:t ->
  response:Response.t option ->
  outcome:Outcome.t ->
  (Assessment.t, Grading_failure.t) result
