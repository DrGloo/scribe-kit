from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


class InstallerTests(unittest.TestCase):
    def test_installs_runtime_without_replacing_existing_hook(self) -> None:
        package_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            subprocess.run(["git", "init", "-q", str(target)], check=True)
            hooks = target / ".githooks"
            hooks.mkdir()
            existing_hook = hooks / "pre-push"
            existing_hook.write_text("#!/bin/sh\necho existing\n", encoding="utf-8")

            subprocess.run(
                ["bash", str(package_root / "install.sh"), str(target)],
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertEqual(
                existing_hook.read_text(encoding="utf-8"),
                "#!/bin/sh\necho existing\n",
            )
            self.assertTrue(
                (target / ".scribe/engineering_scribe/cli.py").is_file()
            )
            self.assertTrue((target / ".github/workflows/scribe.yml").is_file())
            self.assertTrue((target / ".githooks/scribe-pre-push").is_file())


if __name__ == "__main__":
    unittest.main()
