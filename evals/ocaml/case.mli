val resolve_resources :
  task:Ast.task -> resources:Ast.resource_binding list -> (Ast.task, Ast.validation_failure) result
