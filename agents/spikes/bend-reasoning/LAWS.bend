import Base
import ./evidence.bend as Evidence

law derivation_is_not_validation:
  {Evidence.validated(Evidence.Derived{}) == False{} : Bool}

law direction_is_not_validation:
  {Evidence.validated(Evidence.Directed{}) == False{} : Bool}

law unexamined_is_not_validation:
  {Evidence.validated(Evidence.Unexamined{}) == False{} : Bool}

law dependent_observation_is_not_validation:
  for confirmed: Bool
  {Evidence.validated(Evidence.Observed{False{}, confirmed}) == False{} : Bool}

law unconfirmed_observation_is_not_validation:
  for independent: Bool
  {Evidence.validated(Evidence.Observed{independent, False{}}) == False{} : Bool}

law independent_confirmation_validates:
  {Evidence.validated(Evidence.Observed{True{}, True{}}) == True{} : Bool}
