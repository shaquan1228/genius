import Base
import ./policy.bend as Policy

law empty_registry_rejects:
  for sender: U32
  for recipient: U32
  for project: U32
  {Policy.authorize([], sender, recipient, project) == False{} : Bool}

law missing_sender_rejects:
  for recipient_member: Bool
  {Policy.decision(False{}, recipient_member) == False{} : Bool}

law missing_recipient_rejects:
  for sender_member: Bool
  {Policy.decision(sender_member, False{}) == False{} : Bool}
