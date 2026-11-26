import Base

type Support is Data:
  Unexamined{}
  Derived{}
  Directed{}
  Observed{independent: Bool, confirmed: Bool}

def validated(support: Support) -> Bool:
  match support:
    case Unexamined{}:
      False{}
    case Derived{}:
      False{}
    case Directed{}:
      False{}
    case Observed{independent, confirmed}:
      Bool.and(independent, confirmed)

def admit(+support: Support, -validation: {validated(support) == True{} : Bool}) -> Support:
  support
