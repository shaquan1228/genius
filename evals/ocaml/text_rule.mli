type t = private { field : string; min_words : int; max_words : int }

val create : field:string -> min_words:int -> max_words:int -> (t, Validation_failure.t) result
