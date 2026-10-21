import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from evals.python import datasets
from evals.python.datasets import pokerbench
from kernel import Criterion, Task, Value


def _data(*rows: dict[str, object]) -> bytes:
    return json.dumps(list(rows), separators=(",", ":")).encode()


def declarations_assign_stable_ids_and_instruct_json_output() -> None:
    data = _data(
        {"instruction": "Preflop scenario", "output": "call"},
        {"instruction": "Another scenario", "output": "raise 2"},
    )
    tasks = pokerbench.declarations(
        split="preflop", data=data, sha256=hashlib.sha256(data).hexdigest(), count=2
    )
    first = tasks[0]
    assert tuple(task.id for task in tasks) == ("preflop-0000", "preflop-0001")
    assert first.instruction.prompt.endswith('Reply with only JSON: {"action":"<action>"}.')
    assert first.instruction.skill == "reasoning"


def answer_declarations_keep_labels_in_rubric_and_reference() -> None:
    data = _data({"instruction": "Scenario", "output": "call"})
    (task,) = pokerbench.declarations(
        split="preflop", data=data, sha256=hashlib.sha256(data).hexdigest(), count=1
    )
    assert isinstance(task.criterion, Criterion.Answer)
    name, expected = task.criterion.rubric.expected[0]
    assert name == "action"
    assert isinstance(expected, Value.String)
    assert expected.value == "call"


def answer_references_keep_the_annotated_action() -> None:
    data = _data({"instruction": "Scenario", "output": "call"})
    (task,) = pokerbench.declarations(
        split="preflop", data=data, sha256=hashlib.sha256(data).hexdigest(), count=1
    )
    assert isinstance(task.reference.completion, Value.Record)
    reference_action = dict(task.reference.completion.fields)["action"]
    assert isinstance(reference_action, Value.String)
    assert reference_action.value == "call"


def declarations_assign_ids_deterministically() -> None:
    data = _data({"instruction": "Scenario", "output": "check"})
    digest = hashlib.sha256(data).hexdigest()
    first = pokerbench.declarations(split="preflop", data=data, sha256=digest, count=1)
    second = pokerbench.declarations(split="preflop", data=data, sha256=digest, count=1)
    assert tuple(task.id for task in first) == tuple(task.id for task in second)


def public_projection_omits_private_answer_text() -> None:
    data = _data({"instruction": "Scenario", "output": "call"})
    (task,) = pokerbench.declarations(
        split="preflop", data=data, sha256=hashlib.sha256(data).hexdigest(), count=1
    )
    public = Task.project(task=task)
    assert public.prompt.endswith('Reply with only JSON: {"action":"<action>"}.')
    assert "call" not in public.prompt


def public_projection_omits_private_answer_fields() -> None:
    data = _data({"instruction": "Scenario", "output": "call"})
    (task,) = pokerbench.declarations(
        split="preflop", data=data, sha256=hashlib.sha256(data).hexdigest(), count=1
    )
    public = Task.project(task=task)
    assert len(public.files) == 0
    assert not hasattr(public, "criterion")
    assert not hasattr(public, "reference")


def declarations_reject_checksum_and_count_mismatches() -> None:
    data = _data({"instruction": "Scenario", "output": "check"})
    with pytest.raises(ValueError, match="checksum"):
        pokerbench.declarations(split="postflop", data=data, sha256="0" * 64, count=1)
    with pytest.raises(ValueError, match="count"):
        pokerbench.declarations(
            split="postflop", data=data, sha256=hashlib.sha256(data).hexdigest(), count=2
        )


def postflop_declarations_use_postflop_ids() -> None:
    data = _data({"instruction": "Scenario", "output": "raise 2"})
    (task,) = pokerbench.declarations(
        split="postflop", data=data, sha256=hashlib.sha256(data).hexdigest(), count=1
    )
    assert task.id == "postflop-00000"


def declarations_reject_invalid_json_records() -> None:
    with pytest.raises((ValueError, ValidationError)):
        pokerbench.declarations(
            split="preflop",
            data=b"not-json",
            sha256=hashlib.sha256(b"not-json").hexdigest(),
            count=1,
        )
    data = _data({"instruction": "Scenario", "output": 7})
    with pytest.raises(ValidationError):
        pokerbench.declarations(
            split="preflop", data=data, sha256=hashlib.sha256(data).hexdigest(), count=1
        )


def dataset_metadata_pins_both_test_splits() -> None:
    assert (
        pokerbench.info.revision,
        pokerbench.info.count,
        pokerbench.info.attributes["license"],
        pokerbench.info.attributes["preflop_count"],
        pokerbench.info.attributes["preflop_filename"],
        pokerbench.info.attributes["preflop_sha256"],
        pokerbench.info.attributes["postflop_count"],
        pokerbench.info.attributes["postflop_filename"],
        pokerbench.info.attributes["postflop_sha256"],
    ) == (
        "7ac61f961c81a50fc0f667820b2fb0e432dfec0d",
        11000,
        "apache-2.0",
        "1000",
        "preflop_1k_test_set_prompt_and_label.json",
        "221027a6dace36d4ab13eb6c54431d4522f33c24cc9390b36eb31baf2eb825b4",
        "10000",
        "postflop_10k_test_set_prompt_and_label.json",
        "ba4fdbe4dbd0efa1f33b1a5c73fb4e194da3504bcb1a83e68d26392cd27f348c",
    )


def cases_load_both_splits_through_the_dataset_loader(
    tmp_path: Path, *, monkeypatch: pytest.MonkeyPatch
) -> None:
    preflop = _data({"instruction": "Preflop scenario", "output": "call"})
    postflop = _data({"instruction": "Postflop scenario", "output": "raise 2"})
    sources = {
        "preflop": pokerbench.SplitSource(
            "preflop.json", hashlib.sha256(preflop).hexdigest(), 1, 4
        ),
        "postflop": pokerbench.SplitSource(
            "postflop.json", hashlib.sha256(postflop).hexdigest(), 1, 5
        ),
    }
    paths = {}
    for source, data in zip(sources.values(), (preflop, postflop), strict=True):
        path = tmp_path / source.filename
        path.write_bytes(data)
        paths[source.filename] = path
    downloads: list[tuple[str, str, str, str]] = []

    def download(*, repo_id: str, filename: str, repo_type: str, revision: str) -> str:
        downloads.append((repo_id, filename, repo_type, revision))
        return str(paths[filename])

    monkeypatch.setattr(pokerbench, "_SPLITS", sources)
    monkeypatch.setattr(pokerbench, "hf_hub_download", download)
    monkeypatch.setattr(
        pokerbench,
        "info",
        datasets.DatasetInfo(
            source="test",
            revision="test",
            sha256="test",
            count=2,
            attributes={},
        ),
    )
    datasets.clear_cache()
    try:
        dataset = datasets.load_dataset(selection="pokerbench")
    finally:
        datasets.clear_cache()
    assert tuple(dataset.records) == ("preflop-0000", "postflop-00000")
    assert downloads == [
        ("RZ412/PokerBench", "preflop.json", "dataset", pokerbench.REVISION),
        ("RZ412/PokerBench", "postflop.json", "dataset", pokerbench.REVISION),
    ]
