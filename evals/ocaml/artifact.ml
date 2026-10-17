type t = { path : string; content : Content.t }

let create ~path ~content : (t, Validation_failure.t) result =
  Validation.checked (File.path_issues ~field:"artifact.path" ~paths:[ path ]) { path; content }

let resolve ~(artifact : t) ~(resources : Resource_binding.t list) =
  match artifact.content with
  | Content.Inline _ -> Ok artifact
  | Content.Resource { key } -> (
      match List.find_opt (fun (binding : Resource_binding.t) -> binding.key = key) resources with
      | Some binding ->
          Result.map
            (fun content -> { artifact with content })
            (Content.create ~inline:binding.contents ())
      | None ->
          Error
            {
              Validation_failure.case_id = None;
              issues =
                [
                  Validation.issue
                    Validation_code.Missing_resource
                    artifact.path
                    ("Missing resource: " ^ key)
                    [ key ];
                ];
            })
