let whitespace_width text index =
  let length = String.length text in
  let starts value =
    let width = String.length value in
    index + width <= length && String.sub text index width = value
  in
  match text.[index] with
  | '\t' | '\n' | '\011' | '\012' | '\r' | '\028' | '\029' | '\030' | '\031' | ' ' -> 1
  | _ -> (
      let spaces =
        [
          "\194\133";
          "\194\160";
          "\225\154\128";
          "\226\128\128";
          "\226\128\129";
          "\226\128\130";
          "\226\128\131";
          "\226\128\132";
          "\226\128\133";
          "\226\128\134";
          "\226\128\135";
          "\226\128\136";
          "\226\128\137";
          "\226\128\138";
          "\226\128\168";
          "\226\128\169";
          "\226\128\175";
          "\226\129\159";
          "\227\128\128";
        ]
      in
      match List.find_opt starts spaces with None -> 0 | Some value -> String.length value)

let word_count ~text =
  let rec count index in_word total =
    if index = String.length text then total
    else
      let width = whitespace_width text index in
      if width > 0 then count (index + width) false total
      else count (index + 1) true (if in_word then total else total + 1)
  in
  count 0 false 0

let trim ~text =
  let rec bounds index first last =
    if index = String.length text then
      match first with None -> "" | Some start -> String.sub text start (last - start)
    else
      let width = whitespace_width text index in
      if width > 0 then bounds (index + width) first last
      else bounds (index + 1) (match first with None -> Some index | some -> some) (index + 1)
  in
  bounds 0 None 0
