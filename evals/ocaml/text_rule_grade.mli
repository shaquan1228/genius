type t = private {
  field : string;
  passed : bool;
  word_count : int option;
  min_words : int;
  max_words : int;
}

val create : field:string -> word_count:int option -> min_words:int -> max_words:int -> t
