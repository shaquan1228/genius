type t = {
  passed : bool;
  response_present : bool;
  fields : Response_comparison.t;
  text_rule : Text_rule_grade.t option;
}

let create ~response_present ~(fields : Response_comparison.t)
    ~(text_rule : Text_rule_grade.t option) =
  {
    passed =
      (response_present && fields.equal
      && match text_rule with None -> true | Some rule -> rule.passed);
    response_present;
    fields;
    text_rule;
  }
