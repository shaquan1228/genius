let total items =
  List.fold_left (fun sum (price, _quantity) -> sum +. price) 0. items
