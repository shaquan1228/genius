"""Execute Python smoke fixtures and reject seeds, partial fixes, and invalid code."""

import asyncio
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

import pytest
from inspect_ai.util._sandbox.local import LocalSandboxEnvironment

from evals.python import commands, query
from evals.python._kernel import Case, ExecutableChecks
from evals.python.catalog import (
    Selection,
    load_cases,
    reference,
    verifier,
)
from evals.python.integrations.inspect.environments import environment, runtime
from evals.python.integrations.smoke import declarations
from evals.python.tests.support import native_timeout_case

CASES = {case.id: case for case in load_cases()}


def snapshot(directory: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in directory.iterdir()}


def verify(case: Case, *, directory: Path, selection: Selection = "smoke") -> bool:
    checks = verifier(case.id, selection=selection)
    assert isinstance(checks, ExecutableChecks)

    async def execute() -> bool:
        agent = LocalSandboxEnvironment()
        try:
            await agent.exec(["mkdir", "workspace"])
            for name, data in snapshot(directory).items():
                await agent.write_file(f"workspace/{name}", data)
            result = await commands.VerifyCase(
                case_id=case.id,
                selection=selection,
                agent=environment(agent),
                runtime=runtime(agent),
            )
            return result.verification.status == "passed"
        finally:
            await LocalSandboxEnvironment.sample_cleanup(
                "test", None, {"default": agent}, interrupted=False
            )

    return asyncio.run(execute())


def write_files(directory: Path, *, files: Mapping[str, str]) -> None:
    for name, text in files.items():
        (directory / name).write_text(text)


def seed(case_id: str, *, directory: Path) -> Case:
    case = CASES[case_id]
    write_files(directory, files=case.files)
    return case


@pytest.mark.parametrize("case_id", ["clear-task", "known-preflight"])
def seeds_fail_and_solutions_pass_test(*, case_id: str, tmp_path: Path) -> None:
    case = seed(case_id, directory=tmp_path)
    assert not verify(case, directory=tmp_path)
    write_files(tmp_path, files=reference(case.id).solution)
    before = snapshot(tmp_path)
    assert verify(case, directory=tmp_path)
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("term", ["price", "price * max(quantity, 1)"])
def receipt_partial_fixes_fail_test(*, term: str, tmp_path: Path) -> None:
    case = seed("clear-task", directory=tmp_path)
    (tmp_path / "receipt.py").write_text(
        f"def total(items):\n    return sum({term} for price, quantity in items)\n"
    )
    assert not verify(case, directory=tmp_path)


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
def preflight_defaults_overrides_and_validation_test(
    *,
    config: int,
    client: int,
    override: str,
    rejection: bool,
    tmp_path: Path,
) -> None:
    case = seed("known-preflight", directory=tmp_path)
    (tmp_path / "config.py").write_text(f"timeout_seconds = {config}\n")
    source = (
        reference(case.id)
        .solution["client.py"]
        .replace("= 30", f"= {client}")
        .replace("    return value\n", f"    return {override}\n")
    )
    if not rejection:
        source = source.replace(
            '    if value <= 0:\n        raise ValueError("timeout must be positive")\n', ""
        )
    (tmp_path / "client.py").write_text(source)
    assert (verify(case, directory=tmp_path)) == (
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
def compile_and_runtime_errors_fail_test(*, source: str, tmp_path: Path) -> None:
    case = seed("clear-task", directory=tmp_path)
    (tmp_path / "receipt.py").write_text(source)
    assert not verify(case, directory=tmp_path)


@pytest.mark.parametrize(
    ("case_id", "script"),
    [
        ("clear-task", "test_receipt.py"),
        ("known-preflight", "test_client.py"),
    ],
)
def visible_check_command_leaves_no_build_files_test(
    *,
    case_id: str,
    script: str,
    tmp_path: Path,
) -> None:
    seed(case_id, directory=tmp_path)
    before = snapshot(tmp_path)
    result = subprocess.run(
        [sys.executable, "-I", "-B", script],
        check=False,
        cwd=tmp_path,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize(
    ("definition", "filename", "fragment"),
    [
        (declarations.timeout(initial=7, requested=17), "config.py", "timeout_seconds = 7"),
        (declarations.timeout(initial=30, requested=229), "config.py", "timeout_seconds = 30"),
        (declarations.receipt(term="price * max(quantity, 1)"), "receipt.py", "max(quantity, 1)"),
    ],
)
def family_variants_generate_working_seeds_and_solutions_test(
    *,
    definition: query.CaseDefinition,
    filename: str,
    fragment: str,
    tmp_path: Path,
) -> None:
    dataset = query.CompileDataset(cases=(definition,))
    case = load_cases(selection=dataset)[0]
    assert fragment in case.files[filename]
    write_files(tmp_path, files=case.files)
    assert not verify(case, directory=tmp_path, selection=dataset)
    write_files(tmp_path, files=reference(case.id, selection=dataset).solution)
    assert verify(case, directory=tmp_path, selection=dataset)


def native_suite_can_declare_python_candidate_checks_test(tmp_path: Path) -> None:
    suite = tmp_path / "suite.ml"
    expression = native_timeout_case(id_expression='"native"', initial="7", requested="17")
    suite.write_text(f"let cases = [{expression}]\n")
    case = load_cases(selection=suite)[0]
    work = tmp_path / "candidate"
    work.mkdir()
    write_files(work, files=case.files)
    assert not verify(case, directory=work, selection=suite)
    write_files(work, files=reference(case.id, selection=suite).solution)
    assert verify(case, directory=work, selection=suite)
