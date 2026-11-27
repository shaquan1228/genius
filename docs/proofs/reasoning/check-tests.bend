import Base
import ./main.bend as Model

def unittest_observation() -> String:
  "from pathlib import Path\n"
    ++ "import contextlib, sys, unittest\n"
    ++ "class CountingResult(unittest.TextTestResult):\n"
    ++ "    passed = 0\n"
    ++ "    def addSuccess(self, test):\n"
    ++ "        super().addSuccess(test)\n"
    ++ "        self.passed += 1\n"
    ++ "root = Path.cwd().resolve()\n"
    ++ "directory = (root / sys.argv[1]).resolve()\n"
    ++ "if not directory.is_relative_to(root) or not directory.is_dir():\n"
    ++ "    sys.exit('test directory must exist inside the checkout')\n"
    ++ "sys.path.insert(0, str(root))\n"
    ++ "with contextlib.redirect_stdout(sys.stderr):\n"
    ++ "    suite = unittest.defaultTestLoader.discover(str(directory.relative_to(root)), pattern=sys.argv[2])\n"
    ++ "    result = unittest.TextTestRunner(resultclass=CountingResult).run(suite)\n"
    ++ "print(result.passed)\n"
    ++ "sys.exit(0 if result.wasSuccessful() else 1)\n"

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
      do IO<Unit>:
        written: Unit <- IO.print("needs_evidence")
        IO.exit(1)

def unavailable(detail: String) -> IO(Unit):
  do IO<Unit>:
    logged: Unit <- IO.print_err(detail)
    written: Unit <- IO.print("unavailable")
    IO.exit(2)

def check_observation(complete: Bool, code: U32, count: String) -> IO(Unit):
  match complete:
    case False{}:
      unavailable("unittest did not report a passing-test count")
    case True{}:
      observed = Bool.and(U32.is_eq(code, 0), Bool.not(String.starts_with(count, "0")))
      subject: Model.ActionUse = Model.Use{1n, 1n, 2n, False{}}
      ctx: Model.Context<
        Model.ActionUse> = Model.Frame{
        0n,
        subject,
        before_snapshot(observed),
        Nil{},
        Model.NoIntervention{}
      }
      print_decision(Model.premise_gate(ctx))

def evaluate_observation(code: U32, +count: String) -> IO(Unit):
  complete = Bool.and(
    Bool.not(String.is_empty(count)),
    List.all(&2, Char, Char.is_digit, String.to_list(count))
  )
  check_observation(complete, code, count)

def report_run(result: Result<&1, &1, U32 & String, U32 & (String & String)>) -> IO(Unit):
  match result:
    case Done{(code, (stdout, stderr))}:
      do IO<Unit>:
        logged: Unit <- IO.print_err(stderr)
        evaluate_observation(code, String.trim(stdout))
    case Fail{(code, message)}:
      unavailable(message)

def run_suite(directory: String, pattern: String) -> IO(Unit):
  do IO<Unit>:
    result: Result<&1, &1, U32 & String, U32 & (String & String)> <-
      Process.run(
        "python3",
        ["-I", "-B", "-c", unittest_observation(), directory, pattern],
        "",
        2097152,
        120000
      )
    report_run(result)

def check_args(args: List<String>) -> IO(Unit):
  match args:
    case _ <> directory <> Nil{}:
      run_suite(directory, "test*.py")
    case _ <> directory <> pattern <> Nil{}:
      run_suite(directory, pattern)
    case other:
      unavailable("usage: check-tests.sh <suite-directory> [filename-pattern]")

def main() -> IO(Unit):
  do IO<Unit>:
    args: List<String> <- IO.args()
    check_args(args)
