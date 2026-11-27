import Base
import ../types.bend as T
import ./report.bend as Report

# ls-tree returns one entry for a literal path, or an empty response for an
# absent path. A tree, submodule, or absent path has no blob ID.
def blob_id(+entry: String) -> Maybe<&2, String>:
  Bool.pick(Maybe<&2, String>, String.starts_with(entry, "blob "), Some{String.drop(entry, 5n)}, None{})

def report(
  +commit: String,
  +path: String,
  question: T.Question<T.CommittedFile{commit, path}>,
  answer: Result<&1, &1, U32 & String, U32 & (String & String)>
) -> IO(Unit):
  match answer:
    case Done{(0, (stdout, _))}:
      actual = blob_id(String.trim(stdout))
      Report.check(T.CommittedFile{commit, path}, question, T.Returned{actual})
    case other:
      Report.check(T.CommittedFile{commit, path}, question, T.NoResponse{})

def run(+commit: String, +path: String, question: T.Question<T.CommittedFile{commit, path}>) -> IO(Unit):
  command: List<String> = ["--no-replace-objects", "--literal-pathspecs", "ls-tree", "--full-tree",
    "--format=%(objecttype) %(objectname)", commit ++ "^{commit}", "--", path]
  do IO<Unit>:
    answer: Result<&1, &1, U32 & String, U32 & (String & String)> <-
      Process.run("git", command, "", 8192, 10000)
    report(commit, path, question, answer)

def arguments(args: List<String>) -> IO(Unit):
  match args:
    case _ <> commit <> path <> Nil{}:
      run(commit, path, T.DidRespond{})
    case _ <> commit <> path <> expected <> Nil{}:
      run(commit, path, T.CheckPrediction{T.Predict{Some{expected}}})
    case other:
      Report.unavailable("expected a commit and a path, optionally followed by a predicted blob ID")

def main() -> IO(Unit):
  do IO<Unit>:
    args: List<String> <- IO.args()
    arguments(args)
