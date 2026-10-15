"""Verify OCaml module boundaries through independent compilation."""

import subprocess
from pathlib import Path

from evals.python.transport import LIBRARY, OCAML_ROOT, RUNNER, SUITE


def run_modules(directory: Path, *, modules: list[str], probe: str) -> str:
    for name in modules:
        (directory / name).write_text((OCAML_ROOT / name).read_text())
    (directory / "probe.ml").write_text(probe)
    return subprocess.run(
        ["sh", str(RUNNER), *modules, "probe.ml"],
        cwd=directory,
        text=True,
        capture_output=True,
        check=True,
        timeout=30,
    ).stdout


def test_fixture_is_independent_and_overlay_is_explicit(tmp_path: Path) -> None:
    assert (
        run_modules(
            tmp_path,
            modules=["fixture.mli", "fixture.ml"],
            probe="""
let () =
  let base = Fixture.of_files ["config.ml", "initial"] in
  let override = Fixture.of_files ["config.ml", "changed"] in
  assert (Fixture.files base = ["config.ml", "initial"]);
  assert (Fixture.files (Fixture.overlay base ~overrides:override) = ["config.ml", "changed"]);
  assert (try ignore (Fixture.of_files ["a", "one"; "a", "two"]); false
          with Invalid_argument _ -> true)
""",
        )
        == ""
    )


def test_starting_projects_compile_without_eval_or_check_modules(tmp_path: Path) -> None:
    assert (
        run_modules(
            tmp_path,
            modules=["fixture.mli", "fixture.ml", "fixtures.ml"],
            probe="""
let () =
  let project = Fixtures.Receipt.fixture ~bug:Ignore_quantity in
  assert (List.mem_assoc "receipt.ml" (Fixture.files project));
  assert (List.length (Fixture.files project) = 2)
""",
        )
        == ""
    )


def test_checks_compile_without_fixture_modules(tmp_path: Path) -> None:
    assert (
        run_modules(
            tmp_path,
            modules=["response.mli", "response.ml", "criterion.ml"],
            probe="""
let checks = Criterion.ocaml ~sources:["receipt.ml"] ~assertions:["Receipt.total [] = 0."]
let () = match checks with
  | Criterion.Code { sources; program } ->
      assert (sources = ["receipt.ml"]);
      assert (String.length program > 0)
  | Criterion.Answer _ -> assert false
""",
        )
        == ""
    )


def test_suite_is_pure_and_eval_policy_does_not_change_fixture(tmp_path: Path) -> None:
    assert (
        run_modules(
            tmp_path,
            modules=[path.name for path in (*LIBRARY, SUITE)],
            probe="""
let () =
  let original = List.hd Suite.cases in
  let changed = { original with
    Case.instruction = Instruction.make ~skill:"reasoning" ~prompt:"A different instruction";
    criterion = Scenarios.Receipt.(totals [ expect ~items:[] ~total:99.0 ]);
    allowed_files = [];
  } in
  assert (List.length Suite.cases = 4);
  assert (Fixture.files changed.fixture = Fixture.files original.fixture);
  assert (changed.allowed_files = []);
  assert (original.allowed_files = ["receipt.ml"])
""",
        )
        == ""
    )


def test_response_and_criteria_invariants_without_scenarios(tmp_path: Path) -> None:
    assert (
        run_modules(
            tmp_path,
            modules=["response.mli", "response.ml", "criterion.ml"],
            probe="""
let rejected construct =
  assert (try ignore (construct ()); false with Invalid_argument _ -> true)
let () =
  let exact = Response.of_fields ["status", Response.String "ready"; "safe", Response.Bool true] in
  assert (List.length (Response.fields exact) = 2);
  assert (Response.fields Response.empty = []);
  rejected (fun () -> Response.of_fields ["", Response.String "value"]);
  rejected (fun () -> Response.of_fields ["x", Response.Bool true; "x", Response.Bool false]);
  rejected (fun () -> Criterion.text_rule ~field:"" ~min_words:0 ~max_words:1);
  rejected (fun () -> Criterion.text_rule ~field:"note" ~min_words:(-1) ~max_words:1);
  rejected (fun () -> Criterion.text_rule ~field:"note" ~min_words:2 ~max_words:1);
  rejected (fun () -> Criterion.answer ~expected:Response.empty ());
  rejected (fun () -> Criterion.answer ~expected:exact
    ~text_rule:(Criterion.text_rule ~field:"status" ~min_words:0 ~max_words:1) ());
  rejected (fun () -> Criterion.answer ~expected:exact
    ~text_rule:{field="note"; min_words=2; max_words=1} ());
  ignore (Criterion.answer ~expected:exact ());
  ignore (Criterion.answer ~expected:Response.empty
    ~text_rule:(Criterion.text_rule ~field:"note" ~min_words:0 ~max_words:0) ());
  rejected (fun () -> Criterion.ocaml ~sources:[] ~assertions:["true"]);
  rejected (fun () -> Criterion.ocaml ~sources:["a.ml"] ~assertions:[])
""",
        )
        == ""
    )


def test_instruction_and_reference_compile_without_criteria(tmp_path: Path) -> None:
    assert (
        run_modules(
            tmp_path,
            modules=[
                "response.mli",
                "response.ml",
                "fixture.mli",
                "fixture.ml",
                "instruction.ml",
                "reference.ml",
            ],
            probe="""
let () =
  let instruction = Instruction.make ~skill:"reasoning" ~prompt:"An instruction" in
  assert (instruction.prompt = "An instruction");
  let completion = Response.of_fields ["status", Response.String "ready"] in
  let edits = Fixture.of_files ["result.txt", "ready"] in
  let reference = Reference.make ~edits (Structured completion) in
  assert (Fixture.files reference.edits = ["result.txt", "ready"]);
  assert (reference.completion = Structured completion);
  let plain = Reference.make (Plain "done") in
  assert (Fixture.files plain.edits = []);
  assert (plain.completion = Plain "done")
""",
        )
        == ""
    )
