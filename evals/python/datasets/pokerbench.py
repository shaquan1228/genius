import hashlib
from pathlib import Path
from typing import Literal, NamedTuple

from huggingface_hub import hf_hub_download
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from evals.python.dataset import DatasetInfo
from kernel import Criterion, Instruction, Reference, Rubric, Task

Split = Literal["preflop", "postflop"]
REPOSITORY = "RZ412/PokerBench"
REVISION = "7ac61f961c81a50fc0f667820b2fb0e432dfec0d"


class SplitSource(NamedTuple):
    filename: str
    sha256: str
    expected_count: int
    id_width: int


_SPLITS: dict[Split, SplitSource] = {
    "preflop": SplitSource(
        "preflop_1k_test_set_prompt_and_label.json",
        "221027a6dace36d4ab13eb6c54431d4522f33c24cc9390b36eb31baf2eb825b4",
        1000,
        4,
    ),
    "postflop": SplitSource(
        "postflop_10k_test_set_prompt_and_label.json",
        "ba4fdbe4dbd0efa1f33b1a5c73fb4e194da3504bcb1a83e68d26392cd27f348c",
        10000,
        5,
    ),
}

info = DatasetInfo(
    source=f"https://huggingface.co/datasets/{REPOSITORY}",
    revision=REVISION,
    sha256=hashlib.sha256(
        "".join(f"{source.filename}:{source.sha256}\n" for source in _SPLITS.values()).encode()
    ).hexdigest(),
    count=sum(source.expected_count for source in _SPLITS.values()),
    attributes={
        "license": "apache-2.0",
        "preflop_count": str(_SPLITS["preflop"].expected_count),
        "preflop_filename": _SPLITS["preflop"].filename,
        "preflop_sha256": _SPLITS["preflop"].sha256,
        "postflop_count": str(_SPLITS["postflop"].expected_count),
        "postflop_filename": _SPLITS["postflop"].filename,
        "postflop_sha256": _SPLITS["postflop"].sha256,
    },
)


class Scenario(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    instruction: str = Field(min_length=1)
    output: str = Field(min_length=1)


def declarations(*, split: Split, data: bytes, sha256: str, count: int) -> tuple[Task, ...]:
    if hashlib.sha256(data).hexdigest() != sha256:
        raise ValueError("PokerBench test split checksum mismatch")
    rows = TypeAdapter(tuple[Scenario, ...]).validate_json(data)
    if len(rows) != count:
        raise ValueError("PokerBench test split row count mismatch")
    return tuple(
        Task.create(
            id=f"{split}-{index:0{_SPLITS[split].id_width}d}",
            fixture=[],
            instruction=Instruction(
                skill="reasoning",
                prompt=row.instruction + '\n\nReply with only JSON: {"action":"<action>"}.',
            ),
            criterion=Criterion.Answer(
                rubric=Rubric(expected=[("action", row.output)], text_rule=None)
            ),
            allowed_files=[],
            reference=Reference(edits=[], completion={"action": row.output}),
        )
        for index, row in enumerate(rows)
    )


def _download(*, split: Split, source: SplitSource) -> tuple[Task, ...]:
    data = Path(
        hf_hub_download(
            repo_id=REPOSITORY,
            filename=source.filename,
            repo_type="dataset",
            revision=REVISION,
        )
    ).read_bytes()
    return declarations(split=split, data=data, sha256=source.sha256, count=source.expected_count)


def cases() -> tuple[Task, ...]:
    return tuple(
        task for split, source in _SPLITS.items() for task in _download(split=split, source=source)
    )
