let read path =
  let channel = open_in_bin path in
  Fun.protect
    ~finally:(fun () -> close_in channel)
    (fun () -> really_input_string channel (in_channel_length channel))

let () =
  print_endline "let sources = [";
  Array.iteri
    (fun index path ->
      if
        index > 0
        && Filename.dirname path = "."
        && (Filename.check_suffix path ".ml" || Filename.check_suffix path ".mli" || path = "dune")
      then Printf.printf "  (%S, %S);\n" (Filename.basename path) (read path))
    Sys.argv;
  print_endline "]"
