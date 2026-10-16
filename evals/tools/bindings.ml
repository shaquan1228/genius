(* Read the compiler's authoritative signatures; never parse OCaml source text. *)
open Types
open Asttypes

let unsupported message = failwith ("Unsupported OCaml interface: " ^ message)
let quote value = Printf.sprintf "%S" value
let array values = "[" ^ String.concat "," values ^ "]"

let object_ fields =
  "{" ^ String.concat "," (List.map (fun (key, value) -> quote key ^ ":" ^ value) fields) ^ "}"

let rec type_ value =
  match get_desc value with
  | Tconstr (path, arguments, _) ->
      object_
        [
          ("kind", quote "name");
          ("name", quote (Path.name path));
          ("args", array (List.map type_ arguments));
        ]
  | Ttuple items -> object_ [ ("kind", quote "tuple"); ("items", array (List.map type_ items)) ]
  | Tarrow (label, argument, result, _) ->
      let name, optional =
        match label with
        | Nolabel -> ("", false)
        | Labelled name -> (name, false)
        | Optional name -> (name, true)
      in
      let argument =
        match (label, get_desc argument) with
        | Optional _, Tconstr (path, [ inner ], _) when Path.same path Predef.path_option -> inner
        | Optional _, _ -> unsupported "optional argument without option type"
        | _ -> argument
      in
      object_
        [
          ("kind", quote "arrow");
          ("label", quote name);
          ("optional", string_of_bool optional);
          ("argument", type_ argument);
          ("result", type_ result);
        ]
  | Tpoly (body, []) -> type_ body
  | _ -> unsupported "polymorphic, object, package, or row type"

let field value =
  if value.ld_mutable <> Immutable then unsupported "mutable record field";
  object_ [ ("name", quote (Ident.name value.ld_id)); ("type", type_ value.ld_type) ]

let constructor value =
  if value.cd_res <> None then unsupported "GADT constructor";
  let arguments =
    match value.cd_args with
    | Cstr_tuple (([] | [ _ ]) as arguments) -> arguments
    | Cstr_tuple _ -> unsupported "multi-argument constructor"
    | Cstr_record _ -> unsupported "inline record constructor"
  in
  object_
    [ ("name", quote (Ident.name value.cd_id)); ("arguments", array (List.map type_ arguments)) ]

let declaration name value =
  if value.type_params <> [] then unsupported ("parameterized type " ^ name);
  if value.type_private <> Public then unsupported ("private type " ^ name);
  let fields =
    match (value.type_kind, value.type_manifest) with
    | Type_abstract, None -> [ ("kind", quote "abstract") ]
    | Type_abstract, Some manifest -> [ ("kind", quote "alias"); ("type", type_ manifest) ]
    | Type_record (fields, Record_regular), None ->
        [ ("kind", quote "record"); ("fields", array (List.map field fields)) ]
    | Type_variant (constructors, Variant_regular), None ->
        [ ("kind", quote "variant"); ("constructors", array (List.map constructor constructors)) ]
    | _ -> unsupported ("type representation " ^ name)
  in
  object_ (("name", quote name) :: fields)

let rec items signature =
  List.map
    (function
      | Sig_type (id, value, _, Exported) -> declaration (Ident.name id) value
      | Sig_value (id, value, Exported) ->
          object_
            [
              ("kind", quote "value");
              ("name", quote (Ident.name id));
              ("type", type_ value.val_type);
            ]
      | Sig_module (id, Mp_present, { md_type = Mty_signature signature; _ }, _, Exported) ->
          object_
            [
              ("kind", quote "module");
              ("name", quote (Ident.name id));
              ("items", array (items signature));
            ]
      | _ -> unsupported "signature item")
    signature

let signature path =
  let cmi = Cmi_format.read_cmi path in
  object_ [ ("module", quote cmi.cmi_name); ("items", array (items cmi.cmi_sign)) ]

let export_interface paths =
  match paths with
  | [] -> invalid_arg "Expected compiled Ast interface"
  | ast_path :: operations ->
      let ast = (Cmi_format.read_cmi ast_path).cmi_sign in
      let ast_module =
        Path.Pdot (Path.Pident (Ident.create_persistent "Genius_evals_kernel__"), "Ast")
      in
      let substitution =
        List.fold_left
          (fun substitution -> function
            | Sig_type (id, _, _, _) ->
                Subst.add_type_path
                  (Path.Pdot (ast_module, Ident.name id))
                  (Path.Pident id)
                  substitution
            | _ -> unsupported "non-type Ast declaration")
          Subst.identity
          ast
      in
      let ast =
        List.map
          (function
            | Sig_type (id, value, recursive, visibility) when Ident.name id = "fixture" ->
                Sig_type
                  ( id,
                    { value with type_manifest = None; type_kind = Type_abstract },
                    recursive,
                    visibility )
            | item -> item)
          ast
      in
      Printtyp.signature Format.std_formatter ast;
      Format.pp_print_newline Format.std_formatter ();
      List.iter
        (fun path ->
          let cmi = Cmi_format.read_cmi path in
          let name =
            String.sub
              cmi.cmi_name
              (String.length "Genius_evals_kernel__")
              (String.length cmi.cmi_name - String.length "Genius_evals_kernel__")
          in
          let signature = Subst.signature Subst.Keep substitution cmi.cmi_sign in
          Format.printf "module %s : sig@.%a@.end@." name Printtyp.signature signature)
        operations;
      Format.printf "val sources : (string * string) list@."

let () =
  try
    match Array.to_list Sys.argv |> List.tl with
    | "--interface" :: paths -> export_interface paths
    | paths -> print_endline (array (List.map signature paths))
  with Failure message ->
    prerr_endline message;
    exit 1
