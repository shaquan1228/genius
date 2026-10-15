open Fixtures

(* Add cases as values. Families generate their files, checks, and reference edits. *)
let cases = [
  Receipt.case ~id:"clear-task" ~bug:Receipt.Ignore_quantity
    ~examples:[ ([], 0.); ([(3., 4)], 12.); ([(3., 0)], 0.);
                ([(2., 3); (4., 2)], 14.); ([(1.5, 2)], 3.) ];
  Preflight.case ~id:"known-preflight" ~initial_timeout:15 ~requested_timeout:30;
  Decision.cheaper ~id:"small-decision" ~a:10 ~b:8;
  Decision.hindsight ~id:"decision-review";
]

let () = emit cases
