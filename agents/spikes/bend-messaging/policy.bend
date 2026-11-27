import Base

type Participant is Data:
  Participant{id: U32, project: U32}

def member(ps: List<&2, Participant>, +id: U32, +project: U32) -> Bool:
  match ps:
    case Nil{}:
      False{}
    case Con{h, t}:
      match h:
        case Participant{pid, pp}:
          Bool.or(Bool.and(U32.is_eq(pid, id), U32.is_eq(pp, project)), member(t, id, project))

def decision(sender_member: Bool, recipient_member: Bool) -> Bool:
  Bool.and(sender_member, recipient_member)

def authorize(+ps: List<&2, Participant>, sender: U32, recipient: U32, +project: U32) -> Bool:
  decision(member(ps, sender, project), member(ps, recipient, project))
