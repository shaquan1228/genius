type t = private { key : string; contents : string }

val create : key:string -> contents:string -> t
