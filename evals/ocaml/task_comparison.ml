type t = {
  equal : bool;
  id : Comparison.t;
  fixture : Fixture_comparison.t;
  instruction : Comparison.t;
  criterion : Comparison.t;
  allowed_files : Comparison.t;
  reference : Comparison.t;
}

let create ~(id : Comparison.t) ~(fixture : Fixture_comparison.t) ~(instruction : Comparison.t)
    ~(criterion : Comparison.t) ~(allowed_files : Comparison.t) ~(reference : Comparison.t) =
  {
    equal =
      id.equal && fixture.equal && instruction.equal && criterion.equal && allowed_files.equal
      && reference.equal;
    id;
    fixture;
    instruction;
    criterion;
    allowed_files;
    reference;
  }
