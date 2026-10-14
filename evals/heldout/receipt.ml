let () =
  Examples.check ~name:"quantity contributes to total" Receipt.total
    [ ([], 0.);
      ([(3., 4)], 12.);
      ([(3., 0)], 0.);
      ([(2., 3); (4., 2)], 14.);
      ([(1.5, 2)], 3.) ]
