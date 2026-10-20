(* Helpers shared by the exported modules; not part of the public kernel. *)
let whitespace_width text index =
  let starts value =
    let width = String.length value in
    index + width <= String.length text && String.sub text index width = value
  in
  match text.[index] with
  | '\t' | '\n' | '\011' | '\012' | '\r' | '\028' | '\029' | '\030' | '\031' | ' ' -> 1
  | _ -> (
      let spaces =
        [
          "\194\133";
          "\194\160";
          "\225\154\128";
          "\226\128\168";
          "\226\128\169";
          "\226\128\175";
          "\226\129\159";
          "\227\128\128";
        ]
        @ List.init 11 (fun i -> "\226\128" ^ String.make 1 (Char.chr (128 + i)))
      in
      match List.find_opt starts spaces with None -> 0 | Some value -> String.length value)

let word_count text =
  let rec count index in_word total =
    if index = String.length text then total
    else
      let width = whitespace_width text index in
      if width > 0 then count (index + width) false total
      else count (index + 1) true (if in_word then total else total + 1)
  in
  count 0 false 0

let valid_path name =
  name <> ""
  && (match name.[0] with 'a' .. 'z' | 'A' .. 'Z' | '_' -> true | _ -> false)
  && String.for_all
       (function 'a' .. 'z' | 'A' .. 'Z' | '0' .. '9' | '_' | '-' | '.' -> true | _ -> false)
       name

let valid_name name =
  name <> ""
  && (match name.[0] with 'a' .. 'z' -> true | _ -> false)
  && String.for_all (function 'a' .. 'z' | '0' .. '9' | '-' -> true | _ -> false) name

let unique values = List.length values = List.length (List.sort_uniq compare values)

let checked ?case_id rules value =
  match
    List.filter_map
      (fun (ok, field, message) -> if ok then None else Some { Failure.field; message })
      rules
  with
  | [] -> Ok value
  | issues -> Error { Failure.case_id; issues }
