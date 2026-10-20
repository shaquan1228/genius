(* Public case inputs exclude private verifier and reference material. *)
type t = { id : string; skill : string; prompt : string; files : Artifact.t list }

let create ~(task : Task.t) : t =
  let tools =
    match task.criterion with
    | Criterion.Code { verifier } -> verifier.tools
    | Criterion.Answer _ | Criterion.State _ -> []
  in
  let artifact (file : File.t) =
    Result.get_ok
      (Artifact.create
         ~path:file.path
         ~content:(Result.get_ok (Content.create ~inline:file.contents ())))
  in
  {
    id = task.id;
    skill = task.instruction.skill;
    prompt = task.instruction.prompt;
    files = List.map artifact (Fixture.files ~fixture:task.fixture) @ tools;
  }
