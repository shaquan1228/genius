type t = { sources : File.t list }

let current =
  {
    sources =
      List.map
        (fun (path, contents) -> Result.get_ok (File.create ~path ~contents))
        Build_info.sources;
  }
