(* Each dataset adapter is compiled against this interface as Dataset.
   Imported records remain opaque to the shared transport. *)
val info : Ast.dataset_info option
val cases : Ast.case list
val import : string -> Ast.case
