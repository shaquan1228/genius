(* Dataset provenance is separate from execution providers. *)
type t = {
  source : string;
  revision : string;
  sha256 : string;
  count : int;
  attributes : (string * string) list;
}
