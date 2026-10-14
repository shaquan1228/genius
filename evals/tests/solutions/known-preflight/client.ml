let fallback_timeout = 30

let timeout = function
  | None -> fallback_timeout
  | Some value ->
      if value <= 0 then invalid_arg "timeout must be positive";
      value
