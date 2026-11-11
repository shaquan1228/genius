"""Declare executable checks for private Python assertions, and the repo fixtures they read."""

from pathlib import Path

from kernel import Criterion, SourceFile, Verifier

HERE = Path(__file__).parent
REPOS = HERE / "repos"


def checks(*, inputs: tuple[str, ...], program: str) -> Criterion:
    return Criterion.Code(
        verifier=Verifier(
            inputs=inputs,
            files=[SourceFile(path="verifier.py", contents=(HERE / "verifier.py").read_text())],
            tools=[],
            command=("python3", "-I", "verifier.py", *inputs),
            stdin=program,
            timeout_seconds=30,
        )
    )


def repo(name: str) -> dict[str, str]:
    """Every file of the repo fixture ``repos/<name>``, keyed by its workspace path."""
    return {
        path.name: path.read_text(encoding="utf-8") for path in sorted((REPOS / name).iterdir())
    }


def repo_checks(*, original: dict[str, str], program: str) -> Criterion:
    """Checks on ``original``'s files that may call ``repo_support.py`` helpers."""
    support = (HERE / "repo_support.py").read_text()
    return checks(
        inputs=tuple(original),
        program=f"{support}\nORIGINAL.update({original!r})\n\n{program}",
    )
