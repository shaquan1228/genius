type t = {
  field : string;
  passed : bool;
  word_count : int option;
  min_words : int;
  max_words : int;
}

let create ~field ~word_count ~min_words ~max_words =
  let passed =
    match word_count with None -> false | Some count -> min_words <= count && count <= max_words
  in
  { field; passed; word_count; min_words; max_words }
