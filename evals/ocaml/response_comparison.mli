type field_comparison = private {
  name : string;
  before : Response_value.t option;
  after : Response_value.t option;
  equal : bool;
}

type t = private { equal : bool; fields : field_comparison list }

val create : before:Response_field.t list -> after:Response_field.t list -> t
