(* Assessment: a predicate evaluated against one observation, retaining the observation
   behind every check so a result explains itself. Named conjunctions become scores.
   https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
   https://developers.openai.com/api/docs/guides/graders *)
type t =
  | Check of { predicate : Predicate.t; observation : Value.t }
  | All of { checks : (string * t) list }

type score = (string * bool) list

let rec create ~predicate ~observation =
  match predicate with
  | Predicate.All { checks } ->
      All
        {
          checks =
            List.map (fun (name, check) -> (name, create ~predicate:check ~observation)) checks;
        }
  | _ -> Check { predicate; observation }

let rec passed ~assessment =
  match assessment with
  | Check { predicate; observation } -> Predicate.holds ~predicate ~observation
  | All { checks } -> List.for_all (fun (_, check) -> passed ~assessment:check) checks

(* The value a check looked at, for leaf predicates with a path. *)
let observed ~assessment =
  match assessment with
  | Check
      {
        predicate =
          ( Predicate.Present { path }
          | Predicate.Equals { path; _ }
          | Predicate.Within { path; _ }
          | Predicate.Contains { path; _ }
          | Predicate.Words { path; _ } );
        observation;
      } ->
      Value.get ~value:observation ~path
  | Check _ | All _ -> None

let scores ~assessment : score =
  match assessment with
  | All { checks } -> List.map (fun (name, assessment) -> (name, passed ~assessment)) checks
  | Check _ -> [ ("passed", passed ~assessment) ]
