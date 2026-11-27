"""Offline contracts for the Linux CI toolchain installer."""

import os
import platform
import shutil
import sys
import unittest

from fixtures.proofs.toolchain import InstallerFixture


@unittest.skipUnless(
    sys.platform.startswith("linux") and platform.machine() == "x86_64" and shutil.which("zstd"),
    "The proof CI installer requires Linux x86_64 and zstd",
)
class ProofToolchainInstaller(InstallerFixture):
    def test_help_does_not_download_or_install(self):
        result = self.run_installer("--help", TEST_DOWNLOAD_FAIL="1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Linux x86_64", result.stdout)
        self.assert_no_partial_install()

    def test_requires_exactly_one_destination(self):
        for arguments in ((), (self.destination, "extra")):
            with self.subTest(arguments=arguments):
                result = self.run_installer(*arguments)
                self.assertEqual(result.returncode, 2)
                self.assert_no_partial_install()

    def test_existing_destination_is_preserved(self):
        self.destination.mkdir()
        marker = self.destination / "keep"
        marker.write_text("existing installation")
        result = self.run_installer(self.destination)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Destination already exists", result.stderr)
        self.assertEqual(marker.read_text(), "existing installation")

    def test_destination_created_during_download_is_preserved(self):
        self.accept_fixture_checksums()
        result = self.run_installer(self.destination, TEST_RACE_DIR=str(self.destination))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Destination already exists", result.stderr)
        self.assertEqual(list(self.destination.iterdir()), [])
        self.assertEqual(list(self.work.glob(".proof-toolchain.*")), [])

    def test_failed_download_cleans_staging(self):
        result = self.run_installer(self.destination, TEST_DOWNLOAD_FAIL="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Download failed", result.stderr)
        self.assert_no_partial_install()

    def test_real_checksum_verifier_rejects_fixture_archive(self):
        result = self.run_installer(self.destination)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SHA-256 verification failed", result.stderr)
        self.assert_no_partial_install()

    def test_installs_verified_payload_and_exports_github_paths(self):
        self.accept_fixture_checksums()
        github_path, github_env = self.work / "github path", self.work / "github env"
        github_path.touch()
        github_env.touch()
        result = self.run_installer(
            self.destination, GITHUB_PATH=str(github_path), GITHUB_ENV=str(github_env)
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        bend_bin = self.destination / "bend" / "bin"
        lean_bin = self.destination / "lean-4.34.0-linux" / "bin"
        self.assertTrue(os.access(bend_bin / "bend", os.X_OK))
        self.assertTrue(os.access(lean_bin / "lean", os.X_OK))
        self.assertEqual(
            github_path.read_text().splitlines(), [str(bend_bin), str(lean_bin)]
        )
        self.assertEqual(github_env.read_text(), f"BEND_BIN={bend_bin}/bend\n")
        checksums = (self.work / "checksums").read_text()
        self.assertIn(
            "c9ff8d67bd903fb6ad9a26b43d8a62c01021de82a44d55ce4a3dcd4732113d6b",
            checksums,
        )
        self.assertIn(
            "caaa98356098c85dc0fcbbd28e1ec66f39eb6551829972b752ff20e1286b646b",
            checksums,
        )
        self.assertEqual(list(self.work.glob(".proof-toolchain.*")), [])

    def test_local_install_reports_paths_without_github_files(self):
        self.accept_fixture_checksums()
        result = self.run_installer(self.destination)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"Bend: {self.destination}/bend/bin/bend", result.stdout)
        self.assertFalse((self.work / "github path").exists())

    def test_incomplete_github_environment_fails_before_download(self):
        github_path = self.work / "github path"
        github_path.touch()
        result = self.run_installer(self.destination, GITHUB_PATH=str(github_path))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must both name writable files", result.stderr)
        self.assert_no_partial_install()


if __name__ == "__main__":
    unittest.main()
