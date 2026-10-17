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
  let fields =
    match value.cd_args with
    | Cstr_tuple [] -> []
    | Cstr_record fields -> List.map field fields
    | Cstr_tuple _ -> unsupported "unnamed constructor arguments"
  in
  object_ [ ("name", quote (Ident.name value.cd_id)); ("fields", array fields) ]

let declaration name value =
  if value.type_params <> [] then unsupported ("parameterized type " ^ name);
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
  object_
    (("name", quote name) :: ("private", string_of_bool (value.type_private = Private)) :: fields)

let exclusive value =
  List.exists
    (fun attribute -> attribute.Parsetree.attr_name.txt = "python.exclusive")
    value.val_attributes

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
              ("exclusive", string_of_bool (exclusive value));
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
  if paths = [] then invalid_arg "Expected compiled owner interfaces";
  let prefix = "Genius_evals_kernel__" in
  let modules =
    List.map
      (fun path ->
        let cmi = Cmi_format.read_cmi path in
        let name =
          String.sub
            cmi.cmi_name
            (String.length prefix)
            (String.length cmi.cmi_name - String.length prefix)
        in
        (name, cmi))
      paths
  in
  let substitution =
    List.fold_left
      (fun substitution (name, cmi) ->
        let target = Path.Pident (Ident.create_persistent name) in
        let wrapped = Path.Pdot (Path.Pident (Ident.create_persistent prefix), name) in
        substitution
        |> Subst.add_module_path wrapped target
        |> Subst.add_module_path
             (Path.Pident (Ident.create_persistent cmi.Cmi_format.cmi_name))
             target)
      Subst.identity
      modules
  in
  List.iter
    (fun (name, cmi) ->
      let signature = Subst.signature Subst.Keep substitution cmi.Cmi_format.cmi_sign in
      Format.printf "module %s : sig@." name;
      List.iter
        (fun item ->
          Format.printf "%a" Printtyp.signature [ item ];
          (match item with
          | Sig_value (_, value, _) when exclusive value ->
              Format.pp_print_string Format.std_formatter " [@@python.exclusive]"
          | _ -> ());
          Format.printf "@.")
        signature;
      Format.printf "end@.")
    modules;
  Format.printf "val sources : (string * string) list@."

let () =
  try
    match Array.to_list Sys.argv |> List.tl with
    | "--interface" :: paths -> export_interface paths
    | paths -> print_endline (array (List.map signature paths))
  with Failure message ->
    prerr_endline message;
    exit 1
