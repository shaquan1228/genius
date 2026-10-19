"""Exercise a wheel in a fresh environment, from a directory outside the source tree."""

import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]


def run(*args: str, cwd: Path) -> None:
    subprocess.run(args, cwd=cwd, check=True)


def main() -> None:
    with TemporaryDirectory(prefix="genius install ") as directory:
        work = Path(directory)
        run("uv", "build", "--sdist", "--out-dir", str(work), str(ROOT), cwd=work)
        run(
            "uv",
            "build",
            "--wheel",
            "--out-dir",
            str(work),
            str(next(work.glob("*.tar.gz"))),
            cwd=work,
        )
        requirements = subprocess.check_output(
            [
                "uv",
                "--color",
                "never",
                "export",
                "--project",
                str(ROOT),
                "--locked",
                "--no-dev",
                "--no-emit-project",
                "--no-hashes",
            ],
            text=True,
        )
        (work / "requirements.txt").write_text(requirements)
        run("uv", "venv", "--python", sys.executable, str(work / "env"), cwd=work)
        python = work / "env/bin/python"
        run("uv", "pip", "sync", "--python", str(python), str(work / "requirements.txt"), cwd=work)
        run(
            "uv",
            "pip",
            "install",
            "--python",
            str(python),
            "--no-deps",
            str(next(work.glob("*.whl"))),
            cwd=work,
        )
        subprocess.run(
            ["sh", str(ROOT / "bin/kernel_setup.sh")],
            cwd=work,
            check=True,
            env=os.environ | {"KERNEL_PYTHON": str(python)},
        )
        expected_hash = subprocess.check_output(
            [
                sys.executable,
                "-c",
                "from evals.python.integrations.inspect.results import harness_hash; "
                "print(harness_hash())",
            ],
            text=True,
        ).strip()
        code = """
import json, os, resource, sys, time, tracemalloc
from pathlib import Path
start = time.perf_counter()
import evals, kernel
native_import = time.perf_counter() - start
start = time.perf_counter()
from evals.python import datasets
from evals.python.integrations.inspect.results import harness_hash
sdk_import = time.perf_counter() - start
assert Path(evals.__file__).is_relative_to(Path.cwd())
assert Path(kernel.__file__).is_relative_to(Path.cwd())
assert Path(evals.__file__).with_name("py.typed").exists()
assert Path(kernel.__file__).with_name("__init__.pyi").exists()
assert harness_hash() == EXPECTED_HASH
tracemalloc.start()
start = time.perf_counter()
selection = os.environ.get("INSTALL_DATASET", "smoke")
first = datasets.load_dataset(selection=selection)
cold = time.perf_counter() - start
start = time.perf_counter()
assert datasets.load_dataset(selection=selection) is first
warm = time.perf_counter() - start
assert len(first.cases) == {"smoke": 4, "humanevalplus": 164}[selection]
datasets.clear_cache()
assert datasets.load_dataset(selection=selection) is not first
rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
print(json.dumps(dict(dataset=selection, native_import_seconds=native_import,
                     sdk_import_seconds=sdk_import, cold_seconds=cold, warm_seconds=warm,
                     peak_rss_bytes=rss * (1024 if sys.platform == "linux" else 1),
                     python_peak_bytes=tracemalloc.get_traced_memory()[1])))
"""
        code = code.replace("EXPECTED_HASH", repr(expected_hash))
        # -I drops PYTHONPATH and the working directory from import search paths.
        run(str(python), "-I", "-c", code, cwd=work)
        run(str(python), "-I", "-m", "evals.python.integrations.smoke", cwd=work)
        print(json.dumps({"installation": "passed", "python": sys.version.split()[0]}))


if __name__ == "__main__":
    main()
