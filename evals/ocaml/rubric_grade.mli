type t = private {
  passed : bool;
  response_present : bool;
  fields : Response_comparison.t;
  text_rule : Text_rule_grade.t option;
}

val create :
  response_present:bool -> fields:Response_comparison.t -> text_rule:Text_rule_grade.t option -> t
