from evals.python import query


def cases() -> tuple[query.CaseDefinition, ...]:
    return (
        query.CaseDefinition(
            id="external-increment",
            fixture={"solution.ml": "let increment value = value\n"},
            instruction=query.Instruction(
                skill="reasoning", prompt="Fix increment so it adds one to its integer input."
            ),
            criterion=query.CodeCriterion(
                verifier=query.VerifierDefinition(
                    inputs=("solution.ml",),
                    files={"verifier.py": query.Resource(name="ocaml_verifier.py")},
                    tools={"check.sh": query.Resource(name="check.sh")},
                    command=("python3", "-I", "verifier.py", "ocaml", "solution.ml"),
                    stdin=(
                        "let () = assert (Solution.increment 0 = 1); "
                        "assert (Solution.increment (-2) = -1)\n"
                    ),
                    timeout_seconds=30,
                )
            ),
            allowed_files=("solution.ml",),
            reference=query.ReferenceDefinition(
                edits={"solution.ml": "let increment value = value + 1\n"},
                completion=query.PlainCompletion(text="Increment now adds one."),
            ),
        ),
        query.CaseDefinition(
            id="external-plan",
            fixture={},
            instruction=query.Instruction(
                skill="reasoning",
                prompt=(
                    'Reply as JSON with strategy="inspect", safe=true, and a reason '
                    "of one to eight words for checking existing behavior first."
                ),
            ),
            criterion=query.AnswerCriterion(
                expected={"strategy": "inspect", "safe": True},
                text_rule=query.TextRule(field="reason", min_words=1, max_words=8),
            ),
            allowed_files=(),
            reference=query.ReferenceDefinition(
                edits={},
                completion=query.StructuredCompletion(
                    fields={
                        "strategy": "inspect",
                        "safe": True,
                        "reason": "Check existing behavior",
                    }
                ),
            ),
        ),
    )
