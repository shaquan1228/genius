type t = private {
  equal : bool;
  added : File.t list;
  removed : File.t list;
  modified : (File.t * File.t) list;
}

val create : before:File.t list -> after:File.t list -> t
