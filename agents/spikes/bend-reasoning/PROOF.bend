import Base
import ./reasoning.bend as Reasoning
import ./LAWS.bend as Laws

def Laws.derivation_is_not_validation():
  {==}

def Laws.direction_is_not_validation():
  {==}

def Laws.unexamined_is_not_validation():
  {==}

def Laws.dependent_observation_is_not_validation(confirmed):
  {==}

def Laws.unconfirmed_observation_is_not_validation(independent):
  match independent:
    case False{}:
      {==}
    case True{}:
      {==}

def Laws.independent_confirmation_validates():
  {==}
