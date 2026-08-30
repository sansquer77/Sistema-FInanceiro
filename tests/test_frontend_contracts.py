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
        missing = [relative for relative in imports if not (WEB_ROOT / relative.split("?", 1)[0]).resolve().is_file()]
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

    def test_cockpit_has_executive_sticky_and_persistent_disclosure_layout(self) -> None:
        index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")
        cockpit = (MODULE_ROOT / "cockpit-view.js").read_text(encoding="utf-8")

        self.assertIn('class="summary-strip executive-summary-strip"', index)
        self.assertIn('class="cockpit-priority-alerts"', index)
        self.assertLess(index.index('id="cockpitLimitAlert"'), index.index('class="summary-strip executive-summary-strip"'))
        for section in ("planning", "debts", "top-expenses", "top-income"):
            self.assertIn(f'data-cockpit-section="{section}"', index)
        self.assertIn(".dashboard-main:has(#cockpitView:not([hidden])) > .topbar", styles)
        self.assertIn("#cockpitView .cockpit-toolbar", styles)
        self.assertIn("background: var(--bg);", styles)
        self.assertNotIn("#cockpitView .cockpit-toolbar {\n  position: sticky;\n  top: 72px", styles)
        self.assertIn("box-shadow: 0 8px 0 var(--bg)", styles)
        self.assertIn("COCKPIT_DISCLOSURE_KEY", cockpit)
        self.assertIn("localStorage.setItem(COCKPIT_DISCLOSURE_KEY", cockpit)

    def test_forms_share_action_validation_and_busy_state_contracts(self) -> None:
        index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")
        app_source = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
        dom_utils = (MODULE_ROOT / "dom-utils.js").read_text(encoding="utf-8")

        for form_id in (
            "accountForm",
            "creditCardForm",
            "cardTransactionForm",
            "transactionForm",
            "portfolioAssetForm",
            "limitForm",
            "simulationForm",
        ):
            form_markup = index[index.index(f'id="{form_id}"'):]
            self.assertIn('class="form-actions"', form_markup.split("</form>", 1)[0], form_id)
        self.assertIn('class="danger" id="consultorProfileDeleteButton"', index)
        self.assertIn("initializeFormUX();", app_source)
        self.assertIn('form.setAttribute("aria-busy", "true")', dom_utils)
        self.assertIn('control.setAttribute("aria-invalid", "true")', dom_utils)
        self.assertIn('control.setAttribute("aria-describedby"', dom_utils)
        self.assertIn(".form-actions .danger", styles)
        self.assertIn("margin-inline-start: auto", styles)

    def test_header_tables_and_filters_share_global_layout_contracts(self) -> None:
        index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")
        consultor = (MODULE_ROOT / "consultor-view.js").read_text(encoding="utf-8")

        topbar_rule = styles[styles.index(".topbar {"):styles.index(".eyebrow {")]
        self.assertIn("position: sticky", topbar_rule)
        self.assertIn("background: var(--bg)", topbar_rule)
        self.assertIn("border-bottom: 1px solid var(--line)", topbar_rule)
        self.assertNotIn("position: sticky", styles[styles.index(".dashboard-main:has(#cockpitView"):styles.index("#cockpitView .cockpit-toolbar")])
        for toolbar in (
            "invoice-list-toolbar filter-toolbar",
            "transaction-list-toolbar filter-toolbar",
            "operation-history-filters filter-toolbar",
            "instructions-toolbar filter-toolbar",
        ):
            self.assertIn(toolbar, index)
        self.assertIn(".report-table th {\n  position: sticky", styles)
        self.assertIn("scrollbar-gutter: stable", styles)
        self.assertIn('class="report-table-wrap"><table class="report-table consultor-table"', consultor)

    def test_portfolio_and_preferences_tabs_stay_below_global_header(self) -> None:
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")

        for selector in (".portfolio-tabs {", ".user-pref-tabs {"):
            start = styles.index(selector)
            rule = styles[start:styles.index("}", start)]
            self.assertIn("position: sticky", rule)
            self.assertIn("top: 74px", rule)
            self.assertIn("background: var(--bg)", rule)
            self.assertIn("isolation: isolate", rule)
        self.assertIn(".launch-form-sticky {\n  position: sticky;\n  top: 88px", styles)
        self.assertIn(".instructions-toolbar {\n  position: sticky;\n  top: 82px", styles)
        self.assertIn(".transaction-day-heading {\n  position: sticky;\n  top: 82px", styles)

    def test_global_search_is_local_keyboard_accessible_and_preserves_view_context(self) -> None:
        index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        app_source = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
        search_source = (MODULE_ROOT / "global-search.js").read_text(encoding="utf-8")

        self.assertIn('id="globalSearchDialog"', index)
        self.assertIn('id="globalSearchInput" type="search"', index)
        self.assertIn('role="listbox"', index)
        self.assertIn('event.key === "/"', search_source)
        self.assertIn('!trigger.closest("[hidden]")', search_source)
        self.assertIn("state.transactions || []", search_source)
        self.assertIn("state.cardTransactions || []", search_source)
        self.assertIn("state.portfolio?.positions || []", search_source)
        self.assertNotIn("fetch(", search_source)
        self.assertNotIn("api(", search_source)
        self.assertIn("const viewScrollPositions = new Map()", app_source)
        self.assertIn("viewScrollPositions.set(previousView, window.scrollY)", app_source)
        self.assertIn("window.scrollTo({ top: viewScrollPositions.get(view) || 0", app_source)

    def test_density_preference_is_local_persistent_and_layout_safe(self) -> None:
        index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        app_source = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")
        density_utils = (MODULE_ROOT / "density-utils.js").read_text(encoding="utf-8")
        user_admin = (MODULE_ROOT / "user-admin-view.js").read_text(encoding="utf-8")

        self.assertIn('localStorage.getItem("sistemaFinanceiro.density")', index)
        self.assertIn('id="densityPreference"', index)
        self.assertIn('data-density-option="comfortable"', index)
        self.assertIn('data-density-option="compact"', index)
        self.assertIn("applyDensity();", app_source)
        self.assertIn('localStorage.setItem(DENSITY_STORAGE_KEY', density_utils)
        self.assertNotIn("fetch(", density_utils)
        self.assertIn("syncDensityPreference", user_admin)
        self.assertIn(':root[data-density="compact"] .dashboard', styles)
        self.assertIn("min-height: 36px", styles)
        self.assertNotIn(':root[data-density="compact"] {\n  font-size:', styles)

    def test_async_and_empty_states_share_semantic_component(self) -> None:
        index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")
        dom_utils = (MODULE_ROOT / "dom-utils.js").read_text(encoding="utf-8")

        self.assertIn('loading: { title: "Carregando"', dom_utils)
        self.assertIn('error: { title: "Não foi possível concluir"', dom_utils)
        self.assertIn('empty: { title: "Nada por aqui ainda"', dom_utils)
        self.assertIn('role: "alert", live: "assertive"', dom_utils)
        self.assertIn('aria-busy="true"', dom_utils)
        self.assertIn('class="ui-state empty-state state-loading compact"', index)
        self.assertIn(".state-error", styles)
        self.assertIn("@keyframes ui-state-spin", styles)
        self.assertIn("@media (prefers-reduced-motion: reduce)", styles)
        raw_states = []
        for path in MODULE_ROOT.glob("*.js"):
            source = path.read_text(encoding="utf-8")
            if '<div class="empty-state' in source:
                raw_states.append(path.name)
        self.assertEqual(raw_states, [], f"Estados HTML fora do helper compartilhado: {raw_states}")

    def test_final_ux_contracts_are_shared_and_accessible(self) -> None:
        index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        app_source = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")
        dom_utils = (MODULE_ROOT / "dom-utils.js").read_text(encoding="utf-8")
        overlay_utils = (MODULE_ROOT / "overlay-utils.js").read_text(encoding="utf-8")
        data_ux = (MODULE_ROOT / "data-ux.js").read_text(encoding="utf-8")

        self.assertIn("initializeOverlayUX();", app_source)
        self.assertIn("initializeDataUX();", app_source)
        self.assertIn('event.key === "Escape"', overlay_utils)
        self.assertIn('event.key !== "Tab"', overlay_utils)
        self.assertIn('overlay.setAttribute("aria-modal", "true")', overlay_utils)
        self.assertIn("showToast(text)", dom_utils)
        self.assertIn("form-operation-summary", dom_utils)
        self.assertIn("let interacted = false", dom_utils)
        self.assertIn('document.createElement("details")', dom_utils)
        self.assertIn('seriesKind === "single"', dom_utils)
        self.assertIn("summary.open = !isSimple", dom_utils)
        self.assertIn("queueMicrotask(update)", dom_utils)
        self.assertIn("!control.disabled", dom_utils)
        self.assertIn('!control.closest("[hidden]")', dom_utils)
        self.assertIn('aria-sort', data_ux)
        self.assertIn("active-filter-chip", data_ux)
        self.assertIn('id="cockpitLastUpdated"', index)
        self.assertIn('id="portfolioLastUpdated"', index)
        self.assertIn('data-progressive-form data-operation-summary', index)
        self.assertIn(".report-table td:first-child", styles)
        self.assertIn(".toast-region", styles)
        portfolio = (MODULE_ROOT / "portfolio-view.js").read_text(encoding="utf-8")
        transactions = (MODULE_ROOT / "transactions-view.js").read_text(encoding="utf-8")
        asset_autocomplete = (MODULE_ROOT / "asset-autocomplete.js").read_text(encoding="utf-8")
        self.assertIn("data-restore-automatic-quote-payload", portfolio)
        self.assertIn('method: "DELETE"', portfolio)
        self.assertIn('triggerButton.textContent = "Atualizando..."', portfolio)
        self.assertIn('quoteCell?.setAttribute("aria-busy", "true")', portfolio)
        self.assertIn("!options.revalidate", portfolio)
        self.assertIn("loadPortfolio({ revalidate: true })", app_source)
        self.assertLess(
            portfolio.index("const data = formData(portfolioAssetForm);"),
            portfolio.index("setFormBusy(portfolioAssetForm, true);"),
        )
        self.assertIn("portfolio-automatic-quote-button", styles)
        self.assertIn("createAssetAutocomplete", portfolio)
        self.assertIn("createAssetAutocomplete", transactions)
        self.assertIn('document.createElement("datalist")', asset_autocomplete)
        self.assertIn("updateQuantityRedemptionPreview", portfolio)
        self.assertIn('name: "remaining_quantity"', portfolio)
        self.assertIn("quantity: position.quantity || 0", portfolio)
        self.assertIn("portfolio.redemption_history || []", portfolio)
        self.assertIn("Ganho/perda", portfolio)
        self.assertIn("Custo FIFO", portfolio)
        self.assertIn("portfolioAllocationRows", portfolio)
        self.assertIn("/api/portfolio/allocation-goals", portfolio)
        self.assertIn('data-portfolio-tab="goals"', index)
        self.assertIn('id="portfolioGoalsForm"', index)
        self.assertIn('portfolio-view.js?v=157', app_source)
        transition_start = portfolio.index("transitionView(() => {")
        transition_end = portfolio.index("  };", transition_start)
        self.assertIn("renderActivePortfolioTab();", portfolio[transition_start:transition_end])


if __name__ == "__main__":
    unittest.main()
