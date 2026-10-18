type t = private { passed : bool; unexpected_files : string list }

val create : allowed_files:string list -> changed_files:string list -> t
