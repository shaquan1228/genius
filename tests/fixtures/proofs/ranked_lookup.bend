import Base
import ../../../docs/proofs/ranked-lookup.bend as Lookup

type Priority is Data:
  Direct{}
  Reported{}

def priorities() -> List<&2, Priority>:
  [Direct{}, Reported{}]

def same_priority(a: Priority, b: Priority) -> Bool:
  match a b:
    case Direct{} Direct{}: True{}
    case Reported{} Reported{}: True{}
    case _ _: False{}

type SuiteReading is Data:
  SuiteResult{run: Nat, priority: Priority, passed: Bool}

def suite_matches(run: Nat, priority: Priority, reading: SuiteReading) -> Bool:
  SuiteResult{recorded_run, recorded_priority, _} = reading
  Bool.and(Nat.is_eq(run, recorded_run), same_priority(priority, recorded_priority))

def suite_history() -> List<&2, SuiteReading>:
  [SuiteResult{17n, Reported{}, False{}},
   SuiteResult{18n, Direct{}, True{}},
   SuiteResult{17n, Direct{}, True{}}]

def suite_lookup_contract(+run: Nat, +history: List<&2, SuiteReading>)
  -> Lookup.Best(~Nat, ~Priority, ~SuiteReading, ~suite_matches, priorities(), run, history,
    Lookup.best(~Nat, ~Priority, ~SuiteReading, ~suite_matches, priorities(), run, history)):
  Lookup.best_is_best(~Nat, ~Priority, ~SuiteReading, ~suite_matches, priorities(), run, history)

def suite_prefers_direct_evidence() -> {
  Lookup.best(~Nat, ~Priority, ~SuiteReading, ~suite_matches, priorities(), 17n, suite_history()) ==
    [SuiteResult{17n, Direct{}, True{}}] : List<&2, SuiteReading>
}:
  {==}

def suite_can_fall_back() -> {
  Lookup.best(~Nat, ~Priority, ~SuiteReading, ~suite_matches, priorities(), 17n,
    [SuiteResult{17n, Reported{}, False{}}]) ==
    [SuiteResult{17n, Reported{}, False{}}] : List<&2, SuiteReading>
}:
  {==}

type RowKey is Data:
  Row{revision: String, split: String, number: Nat}

type Action is Data:
  Call{}
  Fold{}

type Reference is Data:
  Label{row: RowKey, priority: Priority, action: Action}

def same_row(a: RowKey, b: RowKey) -> Bool:
  Row{revision, split, number} = a
  Row{recorded_revision, recorded_split, recorded_number} = b
  Bool.and(String.eq(revision, recorded_revision),
    Bool.and(String.eq(split, recorded_split), Nat.is_eq(number, recorded_number)))

def row_matches(row: RowKey, priority: Priority, reference: Reference) -> Bool:
  Label{recorded_row, recorded_priority, _} = reference
  Bool.and(same_row(row, recorded_row), same_priority(priority, recorded_priority))

def row() -> RowKey:
  Row{"fixture-revision", "postflop", 42n}

def poker_lookup_contract(+key: RowKey, +history: List<&2, Reference>)
  -> Lookup.Best(~RowKey, ~Priority, ~Reference, ~row_matches, priorities(), key, history,
    Lookup.best(~RowKey, ~Priority, ~Reference, ~row_matches, priorities(), key, history)):
  Lookup.best_is_best(~RowKey, ~Priority, ~Reference, ~row_matches, priorities(), key, history)

def poker_wrong_row_is_unanswered() -> {
  Lookup.best(~RowKey, ~Priority, ~Reference, ~row_matches, priorities(), row(),
    [Label{Row{"fixture-revision", "postflop", 43n}, Direct{}, Call{}}]) ==
    Nil{} : List<&2, Reference>
}:
  {==}

def poker_disagreements_at_the_best_priority_remain_visible() -> {
  Lookup.best(~RowKey, ~Priority, ~Reference, ~row_matches, priorities(), row(),
    [Label{row(), Direct{}, Call{}}, Label{row(), Reported{}, Call{}}, Label{row(), Direct{}, Fold{}}]) ==
    [Label{row(), Direct{}, Call{}}, Label{row(), Direct{}, Fold{}}] : List<&2, Reference>
}:
  {==}
