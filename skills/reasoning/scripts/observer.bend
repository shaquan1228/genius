import Base

# Resolve the observer from the installed checker, independent of the test checkout.
def path(program: String, name: String) -> String:
  parts = List.reverse(&2, String, String.split(program, '/'))
  parents = List.drop(&2, String, parts, 1n)
  directory = String.join(List.reverse(&2, String, parents), "/")
  directory ++ "/" ++ name
