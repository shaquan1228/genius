type t = { name : string; value : Response_value.t }

let create ~name ~value =
  Validation.checked
    (Validation.when_invalid
       (name <> "")
       (Validation.issue
          Validation_code.Invalid_response_field
          "response.name"
          "Response fields need nonempty names"
          [ name ]))
    { name; value }
