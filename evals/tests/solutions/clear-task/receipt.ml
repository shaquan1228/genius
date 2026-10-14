let total items =
  List.fold_left (fun sum (price, quantity) -> sum +. price *. float_of_int quantity) 0. items
