import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "adm" / "atualiza-financeiro.sh"


class ServerDeployScriptContractTests(unittest.TestCase):
    def test_runtime_directories_are_excluded_from_remote_sync(self):
        source = SCRIPT.read_text(encoding="utf-8")

        self.assertIn("rsync -a --delete", source)
        for runtime_directory in ("data/", "secure/", ".venv/"):
            self.assertIn(f"--exclude '{runtime_directory}'", source)

    def test_failure_trap_and_service_validation_are_present(self):
        source = SCRIPT.read_text(encoding="utf-8")

        self.assertIn("trap restart_on_error EXIT", source)
        self.assertIn('systemctl start "$SERVICE" || true', source)
        self.assertIn('systemctl is-active --quiet "$SERVICE"', source)

    def test_source_is_validated_before_service_is_stopped(self):
        source = SCRIPT.read_text(encoding="utf-8")

        stop_position = source.index('systemctl stop "$SERVICE"')
        for validation in (
            'test -f "$SOURCE/app.py"',
            'test -d "$SOURCE/financeiro"',
            'test -d "$SOURCE/web"',
            "command -v rsync >/dev/null",
        ):
            self.assertLess(source.index(validation), stop_position)


if __name__ == "__main__":
    unittest.main()
