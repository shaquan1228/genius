(* Pure case declarations. Importing this module performs no export or execution. *)
let cases = [
  Eval.case ~id:"clear-task"
    ~fixture:(Fixtures.Receipt.fixture ~bug:Ignore_quantity)
    ~task:Task.Receipt.fix_total
    ~checks:(Check.Receipt.total [
      ([], 0.); ([(3., 4)], 12.); ([(3., 0)], 0.);
      ([(2., 3); (4., 2)], 14.); ([(1.5, 2)], 3.);
    ])
    ~allowed_files:["receipt.ml"] ~reference:Reference.receipt;
  Eval.case ~id:"known-preflight"
    ~fixture:(Fixtures.Preflight.fixture ~timeout:15)
    ~task:(Task.Preflight.change_timeout ~initial:15 ~requested:30)
    ~checks:(Check.Preflight.defaults ~timeout:30)
    ~allowed_files:["config.ml"; "client.ml"]
    ~reference:(Reference.preflight ~timeout:30);
  Eval.case ~id:"small-decision" ~fixture:Fixture.empty
    ~task:(Task.Decision.cheaper ~a:10 ~b:8)
    ~checks:(Check.choice B) ~allowed_files:[]
    ~reference:(Reference.reply ~answer:(Choice B)
      ~reason:"B costs less for identical service.");
  Eval.case ~id:"decision-review" ~fixture:Fixture.empty
    ~task:Task.Decision.hindsight
    ~checks:(Check.review ~supported:true ~change_rule:false) ~allowed_files:[]
    ~reference:(Reference.reply ~answer:(Review { supported = true; change_rule = false })
      ~reason:"One loss did not change the known odds.");
]
