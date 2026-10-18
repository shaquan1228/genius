(* Fixture: immutable initial files. The map implementation belongs to Fixture.
   https://inspect.aisi.org.uk/datasets.html#sample-files
   https://docs.harborframework.com/tasks/environment *)
module Files = Map.Make (String)

type t = File.t Files.t

let empty = Files.empty
let files ~fixture = List.map snd (Files.bindings fixture)

let add ~fixture ~(file : File.t) =
  Validation.checked
    (Validation.when_invalid
       (not (Files.mem file.path fixture))
       (Validation.issue
          Validation_code.Duplicate_path
          "fixture"
          ("Duplicate fixture path: " ^ file.path)
          [ file.path ]))
    (Files.add file.path file fixture)

let create ~files =
  List.fold_left
    (fun result file -> Result.bind result (fun fixture -> add ~fixture ~file))
    (Ok empty)
    files

let overlay ~base ~overrides = Files.union (fun _ _ replacement -> Some replacement) base overrides

let compare ~before ~after =
  Fixture_comparison.create ~before:(files ~fixture:before) ~after:(files ~fixture:after)
