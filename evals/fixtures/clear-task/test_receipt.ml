let () =
  Examples.check ~name:"receipt total" Receipt.total
    [ ([], 0.); ([(3., 1); (4., 1)], 7.) ]
