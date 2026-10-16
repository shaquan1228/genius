"""Execute Python smoke fixtures and reject seeds, partial fixes, and invalid code."""

import asyncio
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

import pytest
from inspect_ai.util._sandbox.local import LocalSandboxEnvironment

from evals.python import commands, query
from evals.python.datasets import Selection
from evals.python.datasets import smoke as declarations
from evals.python.integrations.inspect.environments import environment, runtime
from evals.python.tests.declarations import _files, _reference_files
from evals.python.tests.projections import reference, verifier
from kernel import Ast

CASES = {case.id: case for case in query.Cases()}


def _snapshot(directory: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in directory.iterdir()}


def _verify(
    case: Ast.case, *, directory: Path, selection: Selection = "smoke"
) -> bool:
    checks = verifier(case.id, selection=selection)
    assert isinstance(checks, Ast.verifier)

    async def execute() -> bool:
        agent = LocalSandboxEnvironment()
        try:
            await agent.exec(["mkdir", "workspace"])
            for name, data in _snapshot(directory).items():
                await agent.write_file(f"workspace/{name}", data)
            result = await commands.VerifyCase(
                case_id=case.id,
                selection=selection,
                agent=environment(agent),
                runtime=runtime(agent),
            )
            return isinstance(result.verification, Ast.Passed)
        finally:
            await LocalSandboxEnvironment.sample_cleanup(
                "test", None, {"default": agent}, interrupted=False
            )

    return asyncio.run(execute())


def _write_files(directory: Path, *, files: Mapping[str, str]) -> None:
    for name, text in files.items():
        (directory / name).write_text(text)


def _seed(case_id: str, *, directory: Path) -> Ast.case:
    case = CASES[case_id]
    _write_files(directory, files=_files(case.files))
    return case


@pytest.mark.parametrize("case_id", ["clear-task", "known-preflight"])
def seeds_fail_and_solutions_pass(*, case_id: str, tmp_path: Path) -> None:
    case = _seed(case_id, directory=tmp_path)
    assert not _verify(case, directory=tmp_path)
    _write_files(tmp_path, files=_reference_files(reference(case.id)))
    before = _snapshot(tmp_path)
    assert _verify(case, directory=tmp_path)
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("term", ["price", "price * max(quantity, 1)"])
def receipt_partial_fixes_fail(*, term: str, tmp_path: Path) -> None:
    case = _seed("clear-task", directory=tmp_path)
    (tmp_path / "receipt.py").write_text(
        f"def total(items):\n    return sum({term} for price, quantity in items)\n"
    )
    assert not _verify(case, directory=tmp_path)


@pytest.mark.parametrize(
    ("config", "client", "override", "rejection"),
    [
        (30, 30, "value", True),
        (15, 30, "value", True),
        (30, 15, "value", True),
        (30, 30, "30", True),
        (30, 30, "value", False),
    ],
)
def preflight_defaults_overrides_and_validation(
    *,
    config: int,
    client: int,
    override: str,
    rejection: bool,
    tmp_path: Path,
) -> None:
    case = _seed("known-preflight", directory=tmp_path)
    (tmp_path / "config.py").write_text(f"timeout_seconds = {config}\n")
    source = (
        _reference_files(reference(case.id))["client.py"]
        .replace("= 30", f"= {client}")
        .replace("    return value\n", f"    return {override}\n")
    )
    if not rejection:
        source = source.replace(
            '    if value <= 0:\n        raise ValueError("timeout must be positive")\n', ""
        )
    (tmp_path / "client.py").write_text(source)
    assert (_verify(case, directory=tmp_path)) == (
        config == 30 and client == 30 and override == "value" and rejection
    )


@pytest.mark.parametrize(
    "source",
    [
        "def total(:",
        'def total(items):\n    raise RuntimeError("broken")\n',
        "import os\nos._exit(0)\ndef total(items): return 0\n",
    ],
)
def compile_and_runtime_errors_fail(*, source: str, tmp_path: Path) -> None:
    case = _seed("clear-task", directory=tmp_path)
    (tmp_path / "receipt.py").write_text(source)
    assert not _verify(case, directory=tmp_path)


@pytest.mark.parametrize(
    ("case_id", "script"),
    [
        ("clear-task", "test_receipt.py"),
        ("known-preflight", "test_client.py"),
    ],
)
def visible_check_command_leaves_no_build_files(
    *,
    case_id: str,
    script: str,
    tmp_path: Path,
) -> None:
    _seed(case_id, directory=tmp_path)
    before = _snapshot(tmp_path)
    result = subprocess.run(
        [sys.executable, "-I", "-B", script],
        check=False,
        cwd=tmp_path,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize(
    ("definition", "filename", "fragment"),
    [
        (declarations.timeout(initial=7, requested=17), "config.py", "timeout_seconds = 7"),
        (declarations.timeout(initial=30, requested=229), "config.py", "timeout_seconds = 30"),
        (declarations.receipt(term="price * max(quantity, 1)"), "receipt.py", "max(quantity, 1)"),
    ],
)
def family_variants_generate_working_seeds_and_solutions(
    *,
    definition: Ast.task,
    filename: str,
    fragment: str,
    tmp_path: Path,
) -> None:
    dataset = query.CompileDataset(cases=(definition,))
    case = query.Cases(selection=dataset)[0]
    assert fragment in _files(case.files)[filename]
    _write_files(tmp_path, files=_files(case.files))
    assert not _verify(case, directory=tmp_path, selection=dataset)
    _write_files(tmp_path, files=_reference_files(reference(case.id, selection=dataset)))
    assert _verify(case, directory=tmp_path, selection=dataset)
