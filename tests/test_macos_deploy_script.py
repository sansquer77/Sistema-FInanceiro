import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "adm" / "deploy-macos.sh"


class MacOSDeployScriptContractTests(unittest.TestCase):
    def test_staging_sync_excludes_runtime_and_generated_files(self):
        source = SCRIPT.read_text(encoding="utf-8")

        self.assertIn("rsync -avh --progress --delete", source)
        for path in ("data/", "secure/", ".venv/", "__pycache__/", ".DS_Store"):
            self.assertIn(f"--exclude '{path}'", source)

    def test_remote_failure_propagates_and_service_is_validated(self):
        source = SCRIPT.read_text(encoding="utf-8")

        self.assertIn("set -Eeuo pipefail", source)
        self.assertIn('"sudo \'$REMOTE_SCRIPT\'"', source)
        self.assertNotIn("sudo systemctl is-active", source)
        self.assertNotIn("ssh ", source.split("set -Eeuo pipefail", 1)[0])


if __name__ == "__main__":
    unittest.main()
