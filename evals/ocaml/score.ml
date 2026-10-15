(* Score: a grader result. Named boolean correctness and scope results are this
   repository's initial representation, rather than a universal score schema.
   https://developers.openai.com/api/docs/guides/graders
   https://evalscope.readthedocs.io/en/latest/get_started/basic_usage.html *)
type t = (string * bool) list

let of_fields fields =
  let rec validate seen = function
    | [] -> ()
    | (name, _) :: rest ->
        if name = "" || List.mem name seen then invalid_arg "Scores need unique nonempty names";
        validate (name :: seen) rest
  in
  validate [] fields;
  fields

let fields score = score
