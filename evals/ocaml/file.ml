(* Fixture: immutable initial files. The map implementation belongs to Fixture.
   https://inspect.aisi.org.uk/datasets.html#sample-files
   https://docs.harborframework.com/tasks/environment *)
type t = { path : string; contents : string }

let valid_path ~path:name =
  name <> ""
  && (match name.[0] with 'a' .. 'z' | 'A' .. 'Z' | '_' -> true | _ -> false)
  && String.for_all
       (function 'a' .. 'z' | 'A' .. 'Z' | '0' .. '9' | '_' | '-' | '.' -> true | _ -> false)
       name

let path_issues ~field ~paths =
  List.filter_map
    (fun path ->
      if valid_path ~path then None
      else
        Some
          (Validation.issue Validation_code.Invalid_path field ("Invalid path: " ^ path) [ path ]))
    paths

let create ~path ~contents =
  Validation.checked (path_issues ~field:"file.path" ~paths:[ path ]) { path; contents }
