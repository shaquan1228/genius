type t = { changed_files : string list; verification : Verification.t }

val create : changed_files:string list -> verification:Verification.t -> t
