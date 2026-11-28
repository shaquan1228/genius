import Base
import ../types.bend as T

def reading(+asked: T.Source, recorded: T.Source, actual: T.Answer(recorded)) -> T.Observation<asked>:
  match asked recorded:
    case T.CommittedFile{commit, path} T.CommittedFile{other_commit, other_path}:
      matches = Bool.and(String.eq(commit, other_commit), String.eq(path, other_path))
      Bool.pick(T.Observation<T.CommittedFile{commit, path}>, matches, T.Returned{actual}, T.NoResponse{})
    case T.TestSuite{run, dir, pattern} T.TestSuite{other_run, other_dir, other_pattern}:
      matches = Bool.and(String.eq(run, other_run),
        Bool.and(String.eq(dir, other_dir), String.eq(pattern, other_pattern)))
      Bool.pick(T.Observation<T.TestSuite{run, dir, pattern}>, matches, T.Returned{actual}, T.NoResponse{})
    case T.ParserCase{version, input} T.ParserCase{other_version, other_input}:
      matches = Bool.and(String.eq(version, other_version), String.eq(input, other_input))
      Bool.pick(T.Observation<T.ParserCase{version, input}>, matches, T.Returned{actual}, T.NoResponse{})
    case _ _: T.NoResponse{}

def from_fact(+source: T.Source, fact: T.Fact) -> T.Observation<source>:
  match fact:
    case T.Reading{recorded, actual}: reading(source, recorded, actual)
    case _: T.NoResponse{}

def first_response(-source: T.Source, current: T.Observation<source>,
  earlier: Unit -> T.Observation<source>) -> T.Observation<source>:
  match current:
    case T.Returned{value}: T.Returned{value}
    case T.NoResponse{}: earlier(Unit{})

def answer_to(+source: T.Source, facts: List<&2, T.Fact>) -> T.Observation<source>:
  match facts:
    case Nil{}: T.NoResponse{}
    case head <> tail:
      first_response(source, from_fact(source, head), _ => answer_to(source, tail))
