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

    def test_simulations_view_tolerates_mixed_static_asset_versions(self) -> None:
        source = (MODULE_ROOT / "simulations-view.js").read_text(encoding="utf-8")
        index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")

        self.assertIn('document.querySelector("#simulationWeeklyProjection")', source)
        self.assertIn("if (weeklyProjectionElement)", source)
        self.assertIn("response.daily_projection || response.weekly_projection", source)
        self.assertIn("Projeção diária de caixa", index)

    def test_cockpit_uses_progressive_fluid_interactions(self) -> None:
        app_source = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
        cockpit_source = (MODULE_ROOT / "cockpit-view.js").read_text(encoding="utf-8")
        tab_utils = (MODULE_ROOT / "tab-utils.js").read_text(encoding="utf-8")
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")
        index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")

        self.assertIn('id="cockpitView" aria-busy="false"', index)
        self.assertIn("cockpitView.setLoading(true)", app_source)
        self.assertIn("cockpitView.setLoading(false)", app_source)
        self.assertIn("transitionView(updateActivePanel)", cockpit_source)
        self.assertIn('event.key === "ArrowRight"', tab_utils)
        self.assertIn('event.key === "ArrowLeft"', tab_utils)
        self.assertIn("prefers-reduced-motion: reduce", tab_utils)
        self.assertIn("view-transition-name: cockpit-active-panel", styles)
        self.assertIn("#cockpitView.is-refreshing", styles)

    def test_all_analytical_tabsets_share_keyboard_and_transition_helpers(self) -> None:
        modules = {
            name: (MODULE_ROOT / name).read_text(encoding="utf-8")
            for name in ("cockpit-view.js", "portfolio-view.js", "reports-view.js", "consultor-view.js", "user-admin-view.js")
        }
        index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")

        for name, source in modules.items():
            self.assertIn("bindRovingTablist", source, name)
            self.assertIn("syncRovingTabState", source, name)
        for tab_name in ("report-tab", "portfolio-tab", "consultor-subtab", "user-pref-tab"):
            self.assertRegex(index, rf'class="[^"]*{tab_name}[^"]*"[^>]+role="tab"')


if __name__ == "__main__":
    unittest.main()
