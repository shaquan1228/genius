from evals.python import commands


def cases() -> tuple[commands.CaseDefinition, ...]:
    return (
        commands.CaseDefinition(
            id="external-increment",
            fixture={"solution.ml": "let increment value = value\n"},
            instruction=commands.Instruction(
                skill="reasoning", prompt="Fix increment so it adds one to its integer input."
            ),
            criterion=commands.CodeCriterion(
                verifier=commands.VerifierDefinition(
                    inputs=("solution.ml",),
                    files={"verifier.py": commands.Resource(name="ocaml_verifier.py")},
                    tools={"check.sh": commands.Resource(name="check.sh")},
                    command=("python3", "-I", "verifier.py", "ocaml", "solution.ml"),
                    stdin=(
                        "let () = assert (Solution.increment 0 = 1); "
                        "assert (Solution.increment (-2) = -1)\n"
                    ),
                    timeout_seconds=30,
                )
            ),
            allowed_files=("solution.ml",),
            reference=commands.ReferenceDefinition(
                edits={"solution.ml": "let increment value = value + 1\n"},
                completion=commands.PlainCompletion(text="Increment now adds one."),
            ),
        ),
        commands.CaseDefinition(
            id="external-plan",
            fixture={},
            instruction=commands.Instruction(
                skill="reasoning",
                prompt=(
                    'Reply as JSON with strategy="inspect", safe=true, and a reason '
                    "of one to eight words for checking existing behavior first."
                ),
            ),
            criterion=commands.AnswerCriterion(
                expected={"strategy": "inspect", "safe": True},
                text_rule=commands.TextRule(field="reason", min_words=1, max_words=8),
            ),
            allowed_files=(),
            reference=commands.ReferenceDefinition(
                edits={},
                completion=commands.StructuredCompletion(
                    fields={
                        "strategy": "inspect",
                        "safe": True,
                        "reason": "Check existing behavior",
                    }
                ),
            ),
        ),
    )
