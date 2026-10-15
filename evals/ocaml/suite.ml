(* Pure case declarations. Importing this module performs no export or execution. *)
let cases =
  [
    Case.make
      ~id:"clear-task"
      ~fixture:(Fixtures.Receipt.fixture ~bug:Ignore_quantity)
      ~instruction:Scenarios.Receipt.fix_total
      ~criterion:
        Scenarios.Receipt.(
          totals
            [
              expect ~items:[] ~total:0.0;
              expect ~items:[ item ~price:3.0 ~quantity:4 ] ~total:12.0;
              expect ~items:[ item ~price:3.0 ~quantity:0 ] ~total:0.0;
              expect ~items:[ item ~price:2.0 ~quantity:3; item ~price:4.0 ~quantity:2 ] ~total:14.0;
              expect ~items:[ item ~price:1.5 ~quantity:2 ] ~total:3.0;
            ])
      ~allowed_files:[ "receipt.ml" ]
      ~reference:Scenarios.Receipt.reference;
    Case.make
      ~id:"known-preflight"
      ~fixture:(Fixtures.Preflight.fixture ~timeout:15)
      ~instruction:(Scenarios.Preflight.change_timeout ~initial:15 ~requested:30)
      ~criterion:(Scenarios.Preflight.defaults ~timeout:30)
      ~allowed_files:[ "config.ml"; "client.ml" ]
      ~reference:(Scenarios.Preflight.reference ~timeout:30);
    Case.make
      ~id:"small-decision"
      ~fixture:Fixture.empty
      ~instruction:(Scenarios.Decision.cheaper ~a:10 ~b:8)
      ~criterion:(Scenarios.Decision.choice B)
      ~allowed_files:[]
      ~reference:
        (Scenarios.Decision.choice_reference B ~reason:"B costs less for identical service.");
    Case.make
      ~id:"decision-review"
      ~fixture:Fixture.empty
      ~instruction:Scenarios.Decision.hindsight
      ~criterion:(Scenarios.Decision.review ~supported:true ~change_rule:false)
      ~allowed_files:[]
      ~reference:
        (Scenarios.Decision.review_reference
           ~supported:true
           ~change_rule:false
           ~reason:"One loss did not change the known odds.");
  ]
