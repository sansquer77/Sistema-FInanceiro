from __future__ import annotations

import re
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = REPOSITORY_ROOT / "web"
MODULE_ROOT = WEB_ROOT / "modules"


class FrontendModuleContractTest(unittest.TestCase):
    def test_app_module_imports_resolve_to_local_files(self) -> None:
        source = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
        imports = re.findall(r'from\s+["\'](\./[^"\']+)["\']', source)

        self.assertTrue(imports, "app.js deve importar módulos ES locais")
        missing = [relative for relative in imports if not (WEB_ROOT / relative).resolve().is_file()]
        self.assertEqual(missing, [], f"Imports ES sem arquivo correspondente: {missing}")

    def test_all_frontend_modules_are_documented_in_the_frontend_spec(self) -> None:
        spec = (REPOSITORY_ROOT / "docs/specs/frontend-modularizacao.md").read_text(encoding="utf-8")
        undocumented = [path.name for path in MODULE_ROOT.glob("*.js") if f"`{path.name}`" not in spec]

        self.assertEqual(undocumented, [], f"Módulos ausentes da spec de frontend: {undocumented}")

    def test_frontend_remains_native_es_modules_without_generated_artifacts(self) -> None:
        index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")

        self.assertRegex(
            index,
            r'<script[^>]+type=["\']module["\'][^>]+src=["\']/(?:app\.js)(?:\?[^"\']+)?["\']',
        )
        self.assertFalse((REPOSITORY_ROOT / "package.json").exists())
        self.assertFalse((REPOSITORY_ROOT / "node_modules").exists())


if __name__ == "__main__":
    unittest.main()
