type t = private { id : string; skill : string; prompt : string; files : Artifact.t list }

val create : task:Task.t -> t
