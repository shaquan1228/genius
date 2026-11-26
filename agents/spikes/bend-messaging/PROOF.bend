import Base
import ./LAWS.bend as Laws

def Laws.empty_registry_rejects(sender, recipient, project):
  {==}

def Laws.missing_sender_rejects(recipient_member):
  {==}

def Laws.missing_recipient_rejects(sender_member):
  match sender_member:
    case False{}:
      {==}
    case True{}:
      {==}
