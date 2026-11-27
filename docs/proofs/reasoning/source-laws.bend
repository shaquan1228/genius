import Base
import ../types.bend as T
import ./history.bend as History

def file_reading(+commit: String, +path: String, +recorded_commit: String, +recorded_path: String,
  +blob: Maybe<&2, String>) -> {
    History.from_fact(T.CommittedFile{commit, path}, T.Reading{T.CommittedFile{recorded_commit, recorded_path}, blob}) ==
    Bool.pick(T.Observation<T.CommittedFile{commit, path}>,
      Bool.and(String.eq(commit, recorded_commit), String.eq(path, recorded_path)), T.Returned{blob}, T.NoResponse{})
    : T.Observation<T.CommittedFile{commit, path}>}:
  {==}

def suite_reading(+run: String, +dir: String, +pattern: String, +recorded_run: String, +recorded_dir: String,
  +recorded_pattern: String, +passed: Bool) -> {
    History.from_fact(T.TestSuite{run, dir, pattern}, T.Reading{T.TestSuite{recorded_run, recorded_dir, recorded_pattern}, passed}) ==
    Bool.pick(T.Observation<T.TestSuite{run, dir, pattern}>, Bool.and(String.eq(run, recorded_run),
      Bool.and(String.eq(dir, recorded_dir), String.eq(pattern, recorded_pattern))), T.Returned{passed}, T.NoResponse{})
    : T.Observation<T.TestSuite{run, dir, pattern}>}:
  {==}

def parser_reading(+version: String, +input: String, +recorded_version: String, +recorded_input: String,
  +actual: T.ParseOutcome) -> {
    History.from_fact(T.ParserCase{version, input}, T.Reading{T.ParserCase{recorded_version, recorded_input}, actual}) ==
    Bool.pick(T.Observation<T.ParserCase{version, input}>, Bool.and(String.eq(version, recorded_version),
      String.eq(input, recorded_input)), T.Returned{actual}, T.NoResponse{})
    : T.Observation<T.ParserCase{version, input}>}:
  {==}

def DifferentKind(asked: T.Source, recorded: T.Source) -> Data:
  match asked recorded:
    case T.ParserCase{_, _} T.ParserCase{_, _}: Empty
    case T.TestSuite{_, _, _} T.TestSuite{_, _, _}: Empty
    case T.CommittedFile{_, _} T.CommittedFile{_, _}: Empty
    case _ _: Unit

def unrelated_sources(+asked: T.Source, +recorded: T.Source, +actual: T.Answer(recorded),
  different: DifferentKind(asked, recorded))
  -> {History.from_fact(asked, T.Reading{recorded, actual}) == T.NoResponse{} : T.Observation<asked>}:
  match asked recorded:
    case T.ParserCase{_, _} T.ParserCase{_, _}: match different:
    case T.TestSuite{_, _, _} T.TestSuite{_, _, _}: match different:
    case T.CommittedFile{_, _} T.CommittedFile{_, _}: match different:
    case T.ParserCase{_, _} T.TestSuite{_, _, _}: {==}
    case T.ParserCase{_, _} T.CommittedFile{_, _}: {==}
    case T.TestSuite{_, _, _} T.ParserCase{_, _}: {==}
    case T.TestSuite{_, _, _} T.CommittedFile{_, _}: {==}
    case T.CommittedFile{_, _} T.ParserCase{_, _}: {==}
    case T.CommittedFile{_, _} T.TestSuite{_, _, _}: {==}
