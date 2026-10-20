(* Kernel: the compiled sources, for fingerprinting runs against the grading policy. *)
type t = { sources : Task.file list }

let current =
  { sources = List.map (fun (path, contents) -> { Task.path; contents }) Build_info.sources }
