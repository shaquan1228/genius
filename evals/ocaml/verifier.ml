type content = Inline of string | Resource of string

type t = {
  inputs : string list;
  files : (string * content) list;
  tools : (string * content) list;
  command : string list;
  stdin : string;
  timeout_seconds : int;
}

let valid_path name =
  name <> ""
  && (match name.[0] with 'a' .. 'z' | 'A' .. 'Z' | '_' -> true | _ -> false)
  && String.for_all
       (function 'a' .. 'z' | 'A' .. 'Z' | '0' .. '9' | '_' | '-' | '.' -> true | _ -> false)
       name

let make ~inputs ~files ~tools ~command ~stdin ~timeout_seconds =
  let names = inputs @ List.map fst files @ List.map fst tools in
  if inputs = [] || not (List.for_all valid_path names) then invalid_arg "Invalid verifier paths";
  if List.length names <> List.length (List.sort_uniq compare names) then
    invalid_arg "Overlapping verifier paths";
  if command = [] || List.exists (( = ) "") command || timeout_seconds <= 0 then
    invalid_arg "Invalid verifier execution";
  { inputs; files; tools; command; stdin; timeout_seconds }
