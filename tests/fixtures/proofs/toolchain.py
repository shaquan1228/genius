"""Tiny release archives and command stubs for offline installer checks."""

import io
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
INSTALLER = ROOT / ".github" / "scripts" / "install-proof-toolchain.sh"


class InstallerFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        temporary = tempfile.TemporaryDirectory(prefix="proof release fixtures ")
        cls.addClassCleanup(temporary.cleanup)
        cls.assets = Path(temporary.name)
        cls.archive(cls.assets / "bend.tar.gz", "bend/bin/bend", "w:gz")
        lean_tar = cls.assets / "lean.tar"
        cls.archive(lean_tar, "lean-4.34.0-linux/bin/lean", "w")
        subprocess.run(
            ["zstd", "-q", str(lean_tar), "-o", str(cls.assets / "lean.tar.zst")],
            check=True,
        )

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="proof toolchain ")
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        self.commands = self.work / "commands"
        self.commands.mkdir()
        self.destination = self.work / "installed tools"
        self.environment = dict(os.environ)
        self.environment.pop("GITHUB_PATH", None)
        self.environment.pop("GITHUB_ENV", None)
        self.environment.update(
            PATH=str(self.commands) + os.pathsep + os.environ["PATH"],
            TEST_ASSETS=str(self.assets),
            TEST_CHECKSUM_LOG=str(self.work / "checksums"),
        )
        self.fake(
            "curl",
            "if os.environ.get('TEST_DOWNLOAD_FAIL'): sys.exit(22)\n"
            "if target := os.getenv('TEST_RACE_DIR'): pathlib.Path(target).mkdir(exist_ok=True)\n"
            "url = next(a for a in sys.argv if a.startswith('https://'))\n"
            "output = sys.argv[sys.argv.index('--output') + 1]\n"
            "asset = 'bend.tar.gz' if '/bendlang/' in url else 'lean.tar.zst'\n"
            "shutil.copyfile(pathlib.Path(os.environ['TEST_ASSETS']) / asset, output)\n",
        )

    @staticmethod
    def archive(path, executable, mode):
        contents = b"#!/bin/sh\nprintf 'fixture executable\\n'\n"
        with tarfile.open(path, mode) as archive:
            info = tarfile.TarInfo(executable)
            info.mode = 0o755
            info.size = len(contents)
            archive.addfile(info, io.BytesIO(contents))

    def fake(self, name, body):
        executable = self.commands / name
        executable.write_text(
            f"#!{sys.executable}\nimport os, pathlib, shutil, sys\n" + body
        )
        executable.chmod(0o755)

    def accept_fixture_checksums(self):
        # Log the requested release hashes while allowing the tiny fixture archives.
        self.fake(
            "sha256sum",
            "with pathlib.Path(os.environ['TEST_CHECKSUM_LOG']).open('a') as log:\n"
            " log.write(sys.stdin.read())\n",
        )

    def run_installer(self, *arguments, **environment):
        return subprocess.run(
            ["bash", str(INSTALLER), *map(str, arguments)],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
            env=self.environment | environment,
        )

    def assert_no_partial_install(self):
        self.assertFalse(self.destination.exists())
        self.assertEqual(list(self.work.glob(".proof-toolchain.*")), [])
