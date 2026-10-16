module Files = Map.Make (String)

type t = string Files.t

let empty = Files.empty
let mem = Files.mem
let add = Files.add
let overlay base overrides = Files.union (fun _ _ replacement -> Some replacement) base overrides
let files = Files.bindings
