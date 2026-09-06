import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "Sistema Financeiro - Distribuicao" / "INSTRUCOES-SERVIDOR.md"


class ServerDistributionGuideTests(unittest.TestCase):
    def test_guide_is_generic_and_covers_supported_admin_clients(self):
        source = GUIDE.read_text(encoding="utf-8")

        for private_value in (
            "192.168.1.212",
            "sistema-financeiro.net",
            "/Volumes/Endor",
            "deploysf",
            "sansquer",
        ):
            self.assertNotIn(private_value, source)

        self.assertIn("A partir de macOS ou Linux", source)
        self.assertIn("A partir do Windows", source)
        self.assertIn("systemd", source)
        self.assertIn("Nginx", source)
        self.assertIn("HTTPS", source)

    def test_every_distribution_workflow_includes_and_validates_the_guide(self):
        for workflow_name, package_root in (
            ("build-macos.yml", "MacOS/INSTRUCOES-SERVIDOR.md"),
            ("build-windows.yml", "Windows/INSTRUCOES-SERVIDOR.md"),
            ("build-linux.yml", "Linux/INSTRUCOES-SERVIDOR.md"),
        ):
            workflow = (ROOT / ".github" / "workflows" / workflow_name).read_text(
                encoding="utf-8"
            )
            self.assertIn("INSTRUCOES-SERVIDOR.md", workflow)
            self.assertIn(package_root, workflow)


if __name__ == "__main__":
    unittest.main()
