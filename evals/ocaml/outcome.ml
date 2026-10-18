type t = { changed_files : string list; verification : Verification.t }

let create ~changed_files ~verification : t = { changed_files; verification }
