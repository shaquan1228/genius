import Base
import ./main.bend as Model

def before_snapshot(confirmed: Bool) -> List<&2, Model.Fact>:
  match confirmed:
    case True{}:
      Model.Confirmation{1n, Model.Direct{}} <> Nil{}
    case False{}:
      Nil{}

def print_decision(allowed: Bool) -> IO(Unit):
  match allowed:
    case True{}:
      IO.print("confirmed")
    case False{}:
      IO.print("needs_evidence")

def check_args(args: List<String>) -> IO(Unit):
  match args:
    case _ <> observed <> Nil{}:
      ctx: Model.Context<
        Model.ActionUse> = Model.Frame{
        0n,
        Model.Use{1n, 1n, 2n, False{}},
        before_snapshot(String.eq(observed, "passed")),
        Nil{},
        Model.NoIntervention{}
      }
      print_decision(Model.premise_gate(ctx))
    case other:
      IO.exit(2)

def main() -> IO(Unit):
  do IO<Unit>:
    args: List<String> <- IO.args()
    check_args(args)
