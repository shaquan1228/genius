import Base

def keep(-Entry: Data, accepted: Bool, entry: Entry, rest: List<&2, Entry>) -> List<&2, Entry>:
  match accepted:
    case True{}: entry <> rest
    case False{}: rest

def at_priority(~Query: Data, ~Priority: Data, ~Entry: Data,
  ~eligible: Query -> Priority -> Entry -> Bool,
  history: List<&2, Entry>, +query: Query, +priority: Priority) -> List<&2, Entry>:
  match history:
    case Nil{}: Nil{}
    case +entry <> rest:
      keep(Entry, eligible(query, priority, entry), entry,
        at_priority(~Query, ~Priority, ~Entry, ~eligible, rest, query, priority))

def prefer(-Entry: Data, current: List<&2, Entry>, lower: Unit -> List<&2, Entry>) -> List<&2, Entry>:
  match current:
    case Nil{}: lower(Unit{})
    case entry <> rest: entry <> rest

# Pass the priorities from strongest to weakest. The eligibility policy
# checks that an entry answers the query and qualifies at the current
# priority. Choose priorities independently of the prediction being checked.
def best(~Query: Data, ~Priority: Data, ~Entry: Data,
  ~eligible: Query -> Priority -> Entry -> Bool,
  priorities: List<&2, Priority>, +query: Query, +history: List<&2, Entry>) -> List<&2, Entry>:
  match priorities:
    case Nil{}: Nil{}
    case priority <> lower:
      prefer(Entry, at_priority(~Query, ~Priority, ~Entry, ~eligible, history, query, priority),
        _ => best(~Query, ~Priority, ~Entry, ~eligible, lower, query, history))

def Nonempty(-Entry: Data, entries: List<&2, Entry>) -> Data:
  match entries:
    case Nil{}: Empty
    case _ <> _: Unit

def AtPriority(-Entry: Data, +current: List<&2, Entry>, -Lower: Type, +result: List<&2, Entry>) -> Type:
  Or(
    Nonempty(Entry, current) & {result == current : List<&2, Entry>},
    {current == Nil{} : List<&2, Entry>} & Lower
  )

# Every skipped priority has an empty eligible set. At the first populated
# priority the result contains every eligible entry, including tied answers.
def Best(~Query: Data, ~Priority: Data, ~Entry: Data,
  ~eligible: Query -> Priority -> Entry -> Bool,
  priorities: List<&2, Priority>, +query: Query, +history: List<&2, Entry>, +result: List<&2, Entry>) -> Type:
  match priorities:
    case Nil{}: {result == Nil{} : List<&2, Entry>}
    case priority <> lower:
      AtPriority(Entry, at_priority(~Query, ~Priority, ~Entry, ~eligible, history, query, priority),
        Best(~Query, ~Priority, ~Entry, ~eligible, lower, query, history, result), result)

def prefer_is_best(-Entry: Data, +current: List<&2, Entry>, -lower: List<&2, Entry>,
  -Lower: List<&2, Entry> -> Type, prove_lower: Unit -> Lower(lower))
  -> AtPriority(Entry, current, Lower(prefer(Entry, current, _ => lower)), prefer(Entry, current, _ => lower)):
  match current:
    case Nil{}: Inr{({==}, prove_lower(Unit{}))}
    case _ <> _: Inl{(Unit{}, {==})}

def best_is_best(~Query: Data, ~Priority: Data, ~Entry: Data,
  ~eligible: Query -> Priority -> Entry -> Bool,
  +priorities: List<&2, Priority>, +query: Query, +history: List<&2, Entry>)
  -> Best(~Query, ~Priority, ~Entry, ~eligible, priorities, query, history,
    best(~Query, ~Priority, ~Entry, ~eligible, priorities, query, history)):
  match priorities:
    case Nil{}: {==}
    case priority <> lower:
      prefer_is_best(Entry, at_priority(~Query, ~Priority, ~Entry, ~eligible, history, query, priority),
        best(~Query, ~Priority, ~Entry, ~eligible, lower, query, history),
        result => Best(~Query, ~Priority, ~Entry, ~eligible, lower, query, history, result),
        _ => best_is_best(~Query, ~Priority, ~Entry, ~eligible, lower, query, history))
