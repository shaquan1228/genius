type t = private { field : string; min_words : int; max_words : int }

val create : field:string -> min_words:int -> max_words:int -> (t, Validation_failure.t) result
val word_count : text:string -> int
val grade : rule:t -> response:Response.t option -> Text_rule_grade.t
