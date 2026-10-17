type t = { name : string; preamble : string; instructions : string list }

val create : name:string -> preamble:string -> instructions:string list -> t
