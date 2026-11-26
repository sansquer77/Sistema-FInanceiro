from __future__ import annotations

import re
import hashlib
import unittest
from pathlib import Path
from urllib.parse import urlparse


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = REPOSITORY_ROOT / "web"
MODULE_ROOT = WEB_ROOT / "modules"


class FrontendModuleContractTest(unittest.TestCase):
    def test_investment_launch_form_explains_total_and_keeps_costs_optional(self) -> None:
        index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        investment_form = (MODULE_ROOT / "transaction-investment-form.js").read_text(encoding="utf-8")
        transaction_form = index[index.index('id="transactionForm"'):]

        self.assertIn("Total debitado da conta", transaction_form)
        self.assertIn("incluindo os custos da operação", transaction_form)
        self.assertIn("não são somados novamente", transaction_form)
        for field in (
            "investment_brokerage_fee", "investment_exchange_fee",
            "investment_tax", "investment_other_costs",
        ):
            markup = re.search(rf'<input[^>]*name="{re.escape(field)}"[^>]*>', transaction_form)
            self.assertIsNotNone(markup, field)
            self.assertNotIn("required", markup.group(0), field)

        self.assertIn("investmentAmount.required = isInvestment", investment_form)
        self.assertIn("investmentTradingCostFields.hidden = !isInvestment || savings", investment_form)
        self.assertIn("investmentTaxCostFields.hidden = !isInvestment || savings", investment_form)
        self.assertIn("Math.round(quantity * unitPrice * 100) / 100", investment_form)
        self.assertIn("Valor bruto de referência:", investment_form)
        self.assertIn("Calculado por quantidade × preço unitário", transaction_form)
        self.assertIn("A diferença em relação ao total debitado", transaction_form)
        self.assertIn("É apenas uma referência e não altera o lançamento", transaction_form)

    def test_loan_active_and_history_tabs_preserve_distinct_statuses(self) -> None:
        index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        app = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
        loans = (MODULE_ROOT / "loans-view.js").read_text(encoding="utf-8")
        for expected in (
            'data-loan-tab="active"', 'data-loan-tab="history"',
            'id="loanActivePanel"', 'id="loanHistoryPanel"',
            'id="loanHistoryList"', 'id="revolvingLoanHistoryList"',
        ):
            self.assertIn(expected, index)
        self.assertIn('loanHistoryList: document.querySelector("#loanHistoryList")', app)
        self.assertIn('api("/api/loans?include_archived=true")', loans)
        self.assertIn("Arquivado · saldo em aberto", loans)
        self.assertIn("Trocado por outra dívida", loans)
        self.assertIn("bindRovingTablist", loans)

    def test_loan_amortization_result_explains_payment_path_before_cdi_notes(self) -> None:
        loans = (MODULE_ROOT / "loans-view.js").read_text(encoding="utf-8")
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")
        self.assertIn("O prazo cai de ${result.baseline_months} para ${result.months} meses", loans)
        self.assertIn('"Amortização extraordinária agora"', loans)
        self.assertIn('"Prazo sem amortização"', loans)
        self.assertIn('"Prazo com esta amortização"', loans)
        self.assertIn("loan-study-result-primary", loans)
        self.assertIn("loan-study-result-footnote", loans)
        self.assertLess(loans.index("${primaryMessage ?"), loans.index("${notes.map"))

    def test_loans_and_simulations_use_shared_premium_surface_contract(self) -> None:
        index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")
        for selector in (
            "#loansView .loan-data-guidance",
            "#loansView #loanList",
            "#loansView .loan-card",
            "#simulationsView .simulation-shell",
            "#simulationsView .simulations-workspace",
            "#simulationsView .loan-study-result-card",
        ):
            self.assertIn(selector, styles)
        self.assertIn('id="loanActivePanel"', index)
        self.assertIn('id="simulationCashflowPanel"', index)
        self.assertIn('id="simulationLoansPanel"', index)
        self.assertIn('data-simulation-mode-tab="cashflow"', index)
        self.assertIn('data-simulation-mode-tab="loans"', index)

    def test_remaining_modules_use_shared_premium_surface_contract(self) -> None:
        index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")
        for module_id in (
            "accountsView", "creditCardsView", "importsView", "classificationsView",
            "operationHistoryView", "userView", "instructionsView", "aboutView",
        ):
            self.assertIn(f'id="{module_id}"', index)
        for selector in (
            "#accountsView .account-card",
            "#creditCardsView .credit-card-item",
            "#importsView .import-result",
            "#classificationsView .classification-item",
            "#operationHistoryView .operation-log-item",
            "#userView .user-pref-tabs",
            "#instructionsView .instructions-group",
            "#aboutView .about-feature-list span",
        ):
            self.assertIn(selector, styles)
        self.assertIn("font-weight: 650", styles)

    def test_backup_preferences_expose_full_validated_flow(self) -> None:
        index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        app_source = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
        preferences = (MODULE_ROOT / "user-admin-view.js").read_text(encoding="utf-8")
        for expected in (
            'data-user-tab="backup"', 'id="userBackupPanel"', 'id="backupSettingsForm"',
            'id="backupRunForm"', 'id="backupRestoreForm"', 'id="backupRestoreConfirmButton"',
        ):
            self.assertIn(expected, index)
        self.assertIn("backupSettingsForm", app_source)
        self.assertIn('api("/api/backup/settings"', preferences)
        self.assertIn('api("/api/backup/run"', preferences)
        self.assertIn('api("/api/backup/validate"', preferences)
        self.assertIn('api("/api/backup/restore"', preferences)
        self.assertIn("backupRestorePasswordInMemory", preferences)
        self.assertIn("Somente o responsável pela instalação", preferences)

    def test_support_link_is_local_to_about_without_global_widget(self) -> None:
        from html.parser import HTMLParser
        class Links(HTMLParser):
            def __init__(self):
                super().__init__()
                self.sections = []
                self.support_sections = []
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == "section":
                    self.sections.append(attrs)
                if tag == "a":
                    host = urlparse(attrs.get("href", "")).hostname or ""
                    if host == "buymeacoffee.com" or host.endswith(".buymeacoffee.com"):
                        self.support_sections.append(list(self.sections))
            def handle_endtag(self, tag):
                if tag == "section" and self.sections:
                    self.sections.pop()
        html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        parser = Links()
        parser.feed(html)
        self.assertEqual(len(parser.support_sections), 1)
        self.assertTrue(any("about" in str(section).lower() for section in parser.support_sections[0]))
        self.assertNotIn("widget.prod.min.js", html)
        self.assertNotIn("BMC-Widget", html)

    def test_transactions_view_composes_extracted_responsibilities(self) -> None:
        transactions = (MODULE_ROOT / "transactions-view.js").read_text(encoding="utf-8")
        cards = (MODULE_ROOT / "cards-view.js").read_text(encoding="utf-8")
        base_form = (MODULE_ROOT / "transaction-form.js").read_text(encoding="utf-8")

        for module_name in (
            "classification-suggestion.js",
            "transaction-balance-chart.js",
            "transaction-list.js",
            "transaction-form.js",
            "transaction-investment-form.js",
        ):
            self.assertIn(f'from "./{module_name}"', transactions)
        self.assertIn('from "./classification-suggestion.js"', cards)
        self.assertNotIn("sourceToBrl / destinationToBrl", transactions)
        self.assertNotIn("amount * rate", transactions)
        self.assertIn("/api/exchange-rate?", base_form)

    def test_apexcharts_is_pinned_local_and_used_through_shared_adapter(self) -> None:
        index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        adapter = (MODULE_ROOT / "chart-adapter.js").read_text(encoding="utf-8")
        artifact = WEB_ROOT / "vendor/apexcharts/4.7.0/apexcharts.min.js"
        license_file = WEB_ROOT / "vendor/apexcharts/4.7.0/LICENSE"
        chart_views = (
            "cockpit-view.js",
            "trends-view.js",
            "cards-view.js",
            "transaction-balance-chart.js",
            "simulations-view.js",
            "portfolio-chart.js",
            "reports-view.js",
        )

        self.assertIn('src="/vendor/apexcharts/4.7.0/apexcharts.min.js?v=4.7.0"', index)
        self.assertNotRegex(index, r'<script[^>]+src=["\']https?://[^"\']*apexcharts')
        self.assertTrue(artifact.is_file())
        self.assertTrue(license_file.is_file())
        self.assertEqual(
            hashlib.sha256(artifact.read_bytes()).hexdigest(),
            "c46de876c375aab3fbc23d82418f7d77251403335808983d2b832d4a38481948",
        )
        self.assertIn("new globalThis.ApexCharts", adapter)
        self.assertIn("animateGradually: { enabled: false }", adapter)
        self.assertIn("dynamicAnimation: { enabled: false }", adapter)
        self.assertIn("animations: {\n        enabled: false", adapter)
        self.assertLess(adapter.index("...(options.chart || {})"), adapter.index("animations: {"))
        self.assertIn("instance.destroy()", adapter)
        self.assertIn("const chartInstances = new Map()", adapter)
        self.assertIn("new MutationObserver(scheduleDisconnectedChartCleanup)", adapter)
        self.assertIn("if (!element.isConnected) {", adapter)
        self.assertIn("chartDefinitions.delete(element)", adapter)
        self.assertIn('attributeFilter: ["hidden"]', adapter)
        self.assertIn('element.closest("[hidden]")', adapter)
        self.assertIn("destroyAllCharts();", (WEB_ROOT / "app.js").read_text(encoding="utf-8"))
        self.assertIn("destroyDisconnectedCharts();", adapter)
        self.assertNotIn("const chartInstances = new WeakMap()", adapter)
        for name in chart_views:
            source = (MODULE_ROOT / name).read_text(encoding="utf-8")
            self.assertIn('from "./chart-adapter.js"', source, name)
            self.assertNotIn("new ApexCharts", source, name)

    def test_portfolio_analysis_keeps_class_rows_distinct_by_currency(self) -> None:
        portfolio = (MODULE_ROOT / "portfolio-grouping.js").read_text(encoding="utf-8")

        self.assertNotIn('reduce(', portfolio)
        self.assertIn('position.currency', portfolio)

    def test_portfolio_goals_separate_usd_variable_income(self) -> None:
        portfolio = (MODULE_ROOT / "portfolio-grouping.js").read_text(encoding="utf-8")
        backend = (REPOSITORY_ROOT / "financeiro/portfolio.py").read_text(encoding="utf-8")

        self.assertNotIn('aggregatePositions', portfolio)
        self.assertIn('presentation.build_presentation', backend)
        view = (MODULE_ROOT / "portfolio-view.js").read_text(encoding="utf-8")
        self.assertNotIn('.reduce(', view)
        self.assertNotIn('quantity * unitPrice', view)
        self.assertIn('position.result_percent', view)
        self.assertIn('position.day_result_percent', view)
        self.assertIn('"stock_usd": "Renda variável - USD"', backend)

    def test_ai_timeout_field_is_visible_for_remote_presets(self) -> None:
        admin = (MODULE_ROOT / "user-admin-view.js").read_text(encoding="utf-8")
        app = (WEB_ROOT / "app.js").read_text(encoding="utf-8")

        self.assertIn("setAIFieldVisibility(elements.aiConfigTimeoutField, customProvider || remoteProvider);", admin)
        self.assertIn('import { registerUserAdminView } from "./modules/user-admin-view.js?v=178";', app)
        self.assertIn('"deepseek"', admin)
        self.assertIn('provider: elements.aiConfigProvider.value', admin)
        self.assertIn('/api/ai-settings${providerQuery}', admin)

    def test_local_model_uses_default_4096_window_and_recognizes_gpu_device_loss(self) -> None:
        client = (MODULE_ROOT / "webllm-client.js").read_text(encoding="utf-8")

        self.assertIn("const CHAT_OPTIONS = { context_window_size: 4096 };", client)
        self.assertIn('export const DEFAULT_LOCAL_MODEL_ID = "Qwen2.5-1.5B-Instruct-q4f16_1-MLC";', client)
        self.assertIn('const LOW_MEMORY_FALLBACK_MODEL_ID = "gemma3-1b-it-q4f16_1-MLC";', client)
        self.assertIn("Tentando um modelo local mais leve", client)
        self.assertIn("webllm.CreateWebWorkerMLCEngine(engineWorker, selectedModelId, engineConfig, CHAT_OPTIONS)", client)
        self.assertIn("webllm.CreateMLCEngine(selectedModelId, engineConfig, CHAT_OPTIONS)", client)
        self.assertIn("preferMainThread", client)
        self.assertIn('diagnosis.category === "string_error"', client)
        self.assertIn("refreshLocalModel", client)
        self.assertIn("device (was )?lost", client)
        self.assertIn("GPU_MEMORY_PATTERN.test(detail)", client)
        consultor_view = (MODULE_ROOT / "consultor-view.js").read_text(encoding="utf-8")
        self.assertIn('if (!order.includes("remota")) throw localError;', consultor_view)
        self.assertIn('const remoteWasAllowed = order.includes("remota");', consultor_view)
        self.assertIn('renderAnalysisState("Tentando a IA local. Preparando o contexto desta análise…");', consultor_view)
        self.assertIn('"A IA local não concluiu. Tentando a IA remota…"', consultor_view)
        run_analysis = consultor_view[consultor_view.index("async function runAnalysis"):]
        self.assertLess(
            run_analysis.index('const order = consultorConfig?.order || ["local", "deterministica"];'),
            run_analysis.index("try {"),
        )
        for module in ("consultor-view.js", "trends-view.js", "user-admin-view.js"):
            source = (MODULE_ROOT / module).read_text(encoding="utf-8")
            self.assertIn('webllm-client.js?v=182"', source, module)
        admin = (MODULE_ROOT / "user-admin-view.js").read_text(encoding="utf-8")
        html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="aiLocalModel"', html)
        self.assertIn('id="aiLocalModelRefresh"', html)
        self.assertIn("local_model_id: selectedLocalModelId()", admin)

    def test_goal_funding_options_exclude_consolidated_linked_assets(self) -> None:
        limits = (MODULE_ROOT / "limits-view.js").read_text(encoding="utf-8")

        self.assertIn('api("/api/financial-goals/funding-options")', limits)
        self.assertNotIn("const used = new Set(state.financialGoals", limits)
        self.assertNotIn("const assets = new Map()", limits)

    def test_long_lists_use_shared_virtualizer_contract(self) -> None:
        virtualizer = (MODULE_ROOT / "virtual-list.js").read_text(encoding="utf-8")
        transactions = (MODULE_ROOT / "transactions-view.js").read_text(encoding="utf-8")
        reports = (MODULE_ROOT / "reports-view.js").read_text(encoding="utf-8")
        portfolio = (MODULE_ROOT / "portfolio-view.js").read_text(encoding="utf-8")

        self.assertIn("DEFAULT_OVERSCAN = 5", virtualizer)
        self.assertIn("requestAnimationFrame", virtualizer)
        self.assertIn('items.length <= threshold', virtualizer)
        self.assertIn('from "./virtual-list.js"', transactions)
        self.assertIn('from "./virtual-list.js"', reports)
        self.assertIn('from "./virtual-list.js"', portfolio)
        self.assertNotIn('const rows = items.map((transaction) => transactionTemplate', transactions)
        self.assertIn("expanded: isExpanded, virtual: !compact", transactions)
        self.assertIn("renderCollectionRows(rowsContainer, items", transactions)
        self.assertIn("destroyVirtualLists(container)", transactions)
        self.assertIn('DEFAULT_THRESHOLD = 200', virtualizer)
        self.assertIn("pendingReportRankings.push", reports)
        self.assertIn("renderItem: (row, index) => reportRankedRow", reports)
        self.assertIn("else mountReportRanking(list, ranking, index)", reports)
        self.assertNotIn(".outerHTML", reports)
        self.assertIn('positionRows.length > 200', portfolio)
        self.assertIn("virtualGroups.set(groupIndex, positionRows)", portfolio)
        self.assertNotIn("const rows = portfolioPositionRows(group.positions)", portfolio)

    def test_portfolio_analysis_flyout_avoids_persistent_webkit_layers(self) -> None:
        portfolio = (MODULE_ROOT / "portfolio-view.js").read_text(encoding="utf-8")
        portfolio_chart = (MODULE_ROOT / "portfolio-chart.js").read_text(encoding="utf-8")
        portfolio_lifecycle = (MODULE_ROOT / "portfolio-lifecycle.js").read_text(encoding="utf-8")
        app = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")

        self.assertIn("portfolioGroupDrawerList?.replaceChildren()", portfolio)
        self.assertIn("function onLeave()", portfolio)
        self.assertIn("clearPortfolioPresentation", portfolio)
        self.assertIn("portfolioView.onLeave()", app)
        self.assertIn("portfolioView.onEnter()", app)
        self.assertIn("destroyChart(portfolioEvolutionChart)", portfolio_chart)
        self.assertNotIn("function closeReturns()", portfolio_chart)
        self.assertIn('"cdi_return_pct"', portfolio_chart)
        self.assertIn('"ipca_return_pct"', portfolio_chart)
        self.assertIn("REVALIDATE_AFTER_MS = 30_000", portfolio_lifecycle)
        self.assertIn("now - state.portfolioLoadedAt", portfolio_lifecycle)
        hidden_rule = styles[styles.index(".portfolio-group-drawer[hidden] {"):]
        hidden_rule = hidden_rule[:hidden_rule.index("}")]
        self.assertIn("display: none !important", hidden_rule)
        overlay_rule = styles[styles.index(".portfolio-group-drawer .drawer-overlay {"):]
        overlay_rule = overlay_rule[:overlay_rule.index("}")]
        self.assertIn("-webkit-backdrop-filter: none", overlay_rule)
        self.assertIn("backdrop-filter: none", overlay_rule)

    def test_portfolio_events_are_lazy_and_show_gross_estimate(self) -> None:
        index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        facade = (MODULE_ROOT / "portfolio-view.js").read_text(encoding="utf-8")
        events = (MODULE_ROOT / "portfolio-events.js").read_text(encoding="utf-8")
        self.assertIn('data-portfolio-tab="events"', index)
        self.assertIn('activeTab === "events"', facade)
        self.assertIn("portfolioEventsView.load()", facade)
        self.assertIn("/api/portfolio/events", events)
        self.assertIn("amount_per_share_micros", events)
        self.assertIn('from "./virtual-list.js"', events)
        self.assertIn("renderCollectionRows", events)
        self.assertIn("threshold: 60", events)
        self.assertIn("destroyVirtualLists(container)", events)
        self.assertIn("Data ex", events)
        self.assertIn("payment_date", events)
        self.assertIn("Carteira", events)
        self.assertIn("portfolio-events-month", events)
        self.assertIn("formatMonth", events)
        self.assertIn("portfolio-event-empty", events)
        self.assertIn("Estimativa bruta = valor por cota/ação × quantidade atualmente aberta", events)
        self.assertIn("Não é valor líquido", events)
        self.assertIn("estimated_value_micros", events)
        self.assertIn('maximumFractionDigits: 2', events)
        self.assertIn("Proventos futuros anunciados para ações, ETFs e BDRs da carteira.", index)
        self.assertIn("event.source", events)
        self.assertIn('role="columnheader">Fonte', events)
        self.assertIn('state.portfolioTab === "events" && nextTab !== "events"', facade)
        self.assertNotIn("events.map(eventRow)", events)
        self.assertNotIn("position.quantity", events)
        self.assertNotIn("estimated_total", events)

    def test_portfolio_tabs_share_premium_hierarchy_and_compact_reflow(self) -> None:
        index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")
        history = (MODULE_ROOT / "portfolio-view.js").read_text(encoding="utf-8")

        self.assertIn('class="portfolio-tab-intro"', index)
        self.assertIn("portfolio-analysis-grid", index)
        self.assertIn('class="portfolio-goals-guidance"', index)
        self.assertIn('class="portfolio-history-section-heading"', history)
        self.assertIn("align-items: start", styles[styles.index(".portfolio-grid {"):styles.index(".portfolio-goals-grid {")])
        self.assertIn(".portfolio-events-grid {\n    min-width: 940px;", styles)
        self.assertIn(".portfolio-events-grid {\n    min-width: 850px;", styles)

    def test_apexcharts_overlays_races_and_history_bounds_are_guarded(self) -> None:
        portfolio = (MODULE_ROOT / "portfolio-view.js").read_text(encoding="utf-8")
        evolution = (MODULE_ROOT / "report-evolution.js").read_text(encoding="utf-8")
        adapter = (MODULE_ROOT / "chart-adapter.js").read_text(encoding="utf-8")
        cards = (MODULE_ROOT / "cards-view.js").read_text(encoding="utf-8")
        transactions = (MODULE_ROOT / "transaction-balance-chart.js").read_text(encoding="utf-8")
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")

        self.assertIn("portfolioChart.clearEvolution()", portfolio)
        self.assertNotIn("portfolioReturnDrawer", portfolio)
        self.assertIn("const requestId = ++evolutionRequestId", evolution)
        self.assertIn("requestId !== evolutionRequestId || context !== currentEvolutionContext", evolution)
        self.assertIn('height: 92, sparkline: { enabled: true }', cards)
        self.assertIn('height: 92, sparkline: { enabled: true }', transactions)
        self.assertIn("centeredMonthlyPoints(rows", cards)
        self.assertIn("centeredMonthlyPoints(rows", transactions)
        self.assertIn("centeredMonthlyAxis(rows)", cards)
        self.assertIn("centeredMonthlyAxis(rows)", transactions)
        self.assertIn("continuousAreaFill()", cards)
        self.assertIn("continuousAreaFill()", transactions)
        self.assertIn('type: "vertical"', adapter)
        self.assertIn("opacityFrom = 0.36", adapter)
        self.assertIn("opacityTo = 0.04", adapter)
        self.assertIn("stops: [0, 100]", adapter)
        self.assertIn('borderColor: chartToken("--chart-average-line"', cards)
        self.assertIn("borderWidth: 2", cards)
        self.assertIn("tooltip: { enabled: false }", cards)
        self.assertIn("tooltip: { enabled: false }", transactions)
        self.assertIn("min: -0.5", adapter)
        self.assertIn("rows.length - 0.5", adapter)
        self.assertNotIn("centeredValueTooltip", adapter)
        for legacy_symbol in (
            "balanceHistoryChartTop",
            "balanceHistoryChartBaseline",
            "balanceHistoryPath",
            "balanceHistoryAreaPath",
            "smoothBalancePath",
        ):
            self.assertNotIn(legacy_symbol, transactions)
        plot_rule = styles[styles.index(".invoice-history-chart .invoice-history-plot {"):]
        plot_rule = plot_rule[:plot_rule.index("}")]
        self.assertIn("height: 92px", plot_rule)
        self.assertIn("overflow: hidden", plot_rule)
        self.assertNotIn(".invoice-history-apex .apexcharts-tooltip", styles)

    def test_app_module_imports_resolve_to_local_files(self) -> None:
        source = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
        imports = re.findall(r'from\s+["\'](\./[^"\']+)["\']', source)

        self.assertTrue(imports, "app.js deve importar módulos ES locais")
        missing = [relative for relative in imports if not (WEB_ROOT / relative.split("?", 1)[0]).resolve().is_file()]
        self.assertEqual(missing, [], f"Imports ES sem arquivo correspondente: {missing}")

    def test_bank_logo_catalog_assets_exist(self) -> None:
        bank_logos = (MODULE_ROOT / "bank-logos.js").read_text(encoding="utf-8")
        bank_asset_dir = WEB_ROOT / "assets" / "banks"
        network_asset_dir = WEB_ROOT / "assets" / "bandeiras"

        self.assertIn("export const BANK_LOGOS", bank_logos)
        self.assertIn("export const CARD_NETWORK_LOGOS", bank_logos)
        self.assertIn("normalizeBankName", bank_logos)
        self.assertIn("renderBankLogo", bank_logos)
        self.assertIn("renderCardNetworkLogo", bank_logos)
        self.assertIn("attachBankLogoFallbacks", bank_logos)

        bank_entries = re.findall(r'export const BANK_LOGOS = \[.*?\];', bank_logos, re.DOTALL)[0]
        network_entries = re.findall(r'export const CARD_NETWORK_LOGOS = \[.*?\];', bank_logos, re.DOTALL)[0]

        bank_files = re.findall(r'file:\s*"([^"]+)"', bank_entries)
        network_files = re.findall(r'file:\s*"([^"]+)"', network_entries)

        missing_banks = [file for file in bank_files if not (bank_asset_dir / file).is_file()]
        missing_networks = [file for file in network_files if not (network_asset_dir / file).is_file()]
        self.assertEqual(missing_banks, [], f"Assets de banco ausentes: {missing_banks}")
        self.assertEqual(missing_networks, [], f"Assets de bandeira ausentes: {missing_networks}")

        for file in bank_files + network_files:
            self.assertRegex(file, r"^[a-z0-9\-]+\.[a-z0-9]+$", f"Nome de asset fora do padrão ASCII minúsculo: {file}")

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

    def test_simulation_plot_has_its_own_row_below_month_cards(self) -> None:
        source = (MODULE_ROOT / "simulations-view.js").read_text(encoding="utf-8")
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")
        html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        self.assertLess(source.index('class="invoice-history-card'), source.index('class="invoice-history-plot"'))
        self.assertIn('<div class="invoice-history-plot" role="presentation">\n          <div class="invoice-history-apex"></div>', source)
        rule = styles.split(".simulation-chart .invoice-history-plot {", 1)[1].split("}", 1)[0]
        for declaration in ("position: relative", "grid-row: 2", "grid-column: 1 / -1", "height: 170px"):
            self.assertIn(declaration, rule)
        rail = styles.split(".simulation-chart .invoice-history-rail {", 1)[1].split("}", 1)[0]
        self.assertIn("grid-template-rows: auto 170px", rail)
        container = styles.split(".simulation-chart {", 1)[1].split("}", 1)[0]
        self.assertIn("overflow-x: auto", container)
        self.assertLess(html.index('id="simulationChart"'), html.index('id="simulationWeeklyProjection"'))

    def test_initial_states_do_not_mount_empty_import_or_simulation_regions(self) -> None:
        imports = (MODULE_ROOT / "imports-view.js").read_text(encoding="utf-8")
        simulations = (MODULE_ROOT / "simulations-view.js").read_text(encoding="utf-8")
        html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('title: "Pronto para importar"', imports)
        self.assertIn('kind: "loading"', imports)
        self.assertIn('id="simulationEmptyState"', html)
        self.assertIn('id="simulationResultsContent" hidden', html)
        self.assertIn('showEmptyState();', simulations)
        self.assertIn('simulationResultsContent.hidden = false', simulations)

    def test_trends_tooltips_pair_text_and_surface_theme_tokens(self) -> None:
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")
        start = styles.index(".trends-chart .apexcharts-canvas .apexcharts-tooltip,")
        rule = styles[start:styles.index("}", start)]
        for declaration in ("color: var(--ink)", "background: var(--panel)", "border-color: var(--line)",
                            ".apexcharts-xaxistooltip", ".apexcharts-yaxistooltip"):
            self.assertIn(declaration, rule)
        title = styles.split(".trends-chart .apexcharts-canvas .apexcharts-tooltip .apexcharts-tooltip-title {", 1)[1].split("}", 1)[0]
        self.assertIn("color: var(--ink)", title)
        self.assertIn("background: var(--surface-low)", title)
        for direction in ("top", "bottom"):
            arrow = styles.split(f".trends-chart .apexcharts-canvas .apexcharts-xaxistooltip-{direction}::after {{", 1)[1].split("}", 1)[0]
            self.assertIn(f"border-{direction}-color: var(--panel)", arrow)

    def test_trends_chart_uses_available_width_without_horizontal_scroll(self) -> None:
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")
        chart = styles.split(".trends-chart {", 1)[1].split("}", 1)[0]
        apex = styles.split(".trends-apex-chart {", 1)[1].split("}", 1)[0]
        self.assertIn("overflow: visible", chart)
        self.assertIn("width: 100%", apex)
        self.assertIn("min-width: 0", apex)
        self.assertNotIn("min-width: 520px", apex)

    def test_trends_overview_uses_editorial_module_hierarchy(self) -> None:
        source = (MODULE_ROOT / "trends-view.js").read_text(encoding="utf-8")
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")

        self.assertIn("Design system v5.24 — evolução como hero", styles)
        self.assertNotIn("${renderSummaryCard()}", source)
        self.assertIn("${renderSummaryMetrics()}", source)
        self.assertIn('class="trends-section-eyebrow">ACOMPANHAMENTO', source)
        self.assertIn('class="trends-confidence-list"', source)
        self.assertIn("border-left: 3px solid transparent", styles)
        self.assertIn("background: transparent;", styles)

    def test_trends_findings_group_point_events_and_limit_review(self) -> None:
        source = (MODULE_ROOT / "trends-view.js").read_text(encoding="utf-8")
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")

        self.assertIn('class="trends-finding trends-finding-group trends-finding-events info"', source)
        self.assertIn('class="trends-finding trends-finding-group trends-finding-limits warning"', source)
        self.assertIn('class="trends-finding-bullets"', source)
        self.assertIn('finding.tipo === "limite_recorrente"', source)
        self.assertIn('>Revisar limite</small>', source)
        self.assertIn(".trends-finding-group {", styles)
        self.assertIn(".trends-finding-action {", styles)

    def test_subscriptions_overview_matches_complete_item_set(self) -> None:
        source = (MODULE_ROOT / "trends-view.js").read_text(encoding="utf-8")
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")

        self.assertNotIn("items.slice(0, 6)", source)
        self.assertIn("${items.map((item) => `", source)
        self.assertIn("Ver detalhes completos", source)
        self.assertIn(".subscriptions-overview-total > div + div", styles)
        self.assertIn(".subscriptions-overview-list", styles)

    def test_portfolio_return_tooltip_reuses_theme_contrast_rules(self) -> None:
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")
        cases = {
            ".apexcharts-tooltip,": ("color: var(--ink)", "background: var(--panel)"),
            ".apexcharts-tooltip .apexcharts-tooltip-title,": ("color: var(--ink)", "background: var(--surface-low)"),
            ".apexcharts-xaxistooltip-bottom::after,": ("border-bottom-color: var(--panel)",),
            ".apexcharts-xaxistooltip-top::after,": ("border-top-color: var(--panel)",),
        }
        for selector, declarations in cases.items():
            rule = styles.split(f".portfolio-return-chart .apexcharts-canvas {selector}", 1)[1].split("}", 1)[0]
            self.assertIn(".trends-chart", rule)
            for declaration in declarations:
                self.assertIn(declaration, rule)

    def test_simulations_view_tolerates_mixed_static_asset_versions(self) -> None:
        source = (MODULE_ROOT / "simulations-view.js").read_text(encoding="utf-8")
        index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")

        self.assertIn('document.querySelector("#simulationWeeklyProjection")', source)
        self.assertIn("if (weeklyProjectionElement)", source)
        self.assertIn("response.daily_projection || response.weekly_projection", source)
        self.assertIn("Projeção diária de caixa", index)

    def test_cockpit_uses_progressive_fluid_interactions(self) -> None:
        loader_source = (MODULE_ROOT / "app-data-loader.js").read_text(encoding="utf-8")
        cockpit_source = (MODULE_ROOT / "cockpit-view.js").read_text(encoding="utf-8")
        tab_utils = (MODULE_ROOT / "tab-utils.js").read_text(encoding="utf-8")
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")
        index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")

        self.assertIn('id="cockpitView" aria-busy="false"', index)
        self.assertIn("cockpit.setLoading(true)", loader_source)
        self.assertIn("cockpit.setLoading(false)", loader_source)
        self.assertIn("transitionView(updateActivePanel)", cockpit_source)
        self.assertIn('event.key === "ArrowRight"', tab_utils)
        self.assertIn('event.key === "ArrowLeft"', tab_utils)
        self.assertIn("prefers-reduced-motion: reduce", tab_utils)
        self.assertIn("view-transition-name: cockpit-active-panel", styles)
        self.assertIn("#cockpitView.is-refreshing", styles)

    def test_app_keeps_composition_root_and_extracted_application_services(self) -> None:
        app_source = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
        state_source = (MODULE_ROOT / "app-state.js").read_text(encoding="utf-8")
        loader_source = (MODULE_ROOT / "app-data-loader.js").read_text(encoding="utf-8")

        self.assertIn("const state = createAppState", app_source)
        self.assertIn("const appDataLoader = createAppDataLoader", app_source)
        self.assertIn("async function boot()", app_source)
        self.assertIn("function resetSessionState()", app_source)
        self.assertIn("function showModule(view)", app_source)
        self.assertNotIn("async function loadAll()", app_source)
        self.assertIn("export function createAppState", state_source)
        self.assertIn("export function resetSessionData", state_source)
        self.assertNotIn("document.", state_source)
        self.assertNotIn("api(", state_source)
        self.assertIn("export function createAppDataLoader", loader_source)
        self.assertIn("getViews", loader_source)
        self.assertNotIn("document.", loader_source)
        self.assertNotIn('fetchAllListed("/api/transactions", "transactions")', loader_source)
        self.assertNotIn('fetchAllListed("/api/credit-card-payments", "payments")', loader_source)
        self.assertIn('/api/transactions?month=', loader_source)
        self.assertIn('/api/credit-card-transactions?month=', loader_source)
        self.assertNotIn('from "./', loader_source)

    def test_cards_loads_only_selected_invoice_and_bounded_history(self) -> None:
        cards_source = (MODULE_ROOT / "cards-view.js").read_text(encoding="utf-8")
        state_source = (MODULE_ROOT / "app-state.js").read_text(encoding="utf-8")

        self.assertIn("response.history || []", cards_source)
        self.assertIn("cardInvoiceHistory", state_source)
        self.assertNotIn('fetchAllListed("/api/credit-card-transactions"', cards_source)
        self.assertNotIn('fetchAllListed("/api/credit-card-payments"', cards_source)

    def test_safari_data_detection_is_disabled_without_overriding_system_fonts(self) -> None:
        index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")

        self.assertIn(
            '<meta name="format-detection" content="telephone=no, date=no, address=no, email=no">',
            index,
        )
        self.assertIn("system-ui", styles)
        self.assertIn("-apple-system", styles)

    def test_heavy_view_loads_share_freshness_invalidation_and_inflight_policy(self) -> None:
        app = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
        api = (MODULE_ROOT / "api.js").read_text(encoding="utf-8")
        policy = (MODULE_ROOT / "load-policy.js").read_text(encoding="utf-8")
        history = (MODULE_ROOT / "operation-history-view.js").read_text(encoding="utf-8")
        preferences = (MODULE_ROOT / "user-admin-view.js").read_text(encoding="utf-8")
        transactions = (MODULE_ROOT / "transaction-slice-loader.js").read_text(encoding="utf-8")
        simulations = (MODULE_ROOT / "simulations-view.js").read_text(encoding="utf-8")

        self.assertIn("let dirty = true", policy)
        self.assertIn("let loadedAt = 0", policy)
        self.assertIn("let inFlight = null", policy)
        self.assertIn("revision === loadRevision", policy)
        self.assertIn("onMutation: handleDataMutation", app)
        self.assertIn("notifyMutation(path, options.method)", api)
        self.assertIn("markDirty: loadPolicy.markDirty", history)
        self.assertIn("loadPreferences", preferences)
        self.assertIn("markPreferencesDirty", preferences)
        self.assertIn('const key = `${accountId}:${month}`', transactions)
        self.assertIn("const snapshots = new Map()", transactions)
        self.assertIn("const requests = new Map()", transactions)
        self.assertIn("while (snapshots.size > maxEntries)", transactions)
        self.assertIn("revision === loadRevision", transactions)
        self.assertIn("markFormDataDirty", simulations)
        self.assertIn("resetPreferencesCache", app)
        self.assertIn("resetTransactionSliceCache", app)

    def test_paid_card_invoice_is_not_subtracted_twice_from_cockpit_forecast(self) -> None:
        projection_source = (REPOSITORY_ROOT / "financeiro/balance_projections.py").read_text(encoding="utf-8")

        self.assertIn("0 if is_invoice_paid", projection_source)
        self.assertIn("-max(open_cents - reserved, 0)", projection_source)
        self.assertNotIn("preferredCardForecastAmount", (WEB_ROOT / "app.js").read_text(encoding="utf-8"))

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
        self.assertLess(index.index('id="cockpitVersionAlert"'), index.index('class="summary-strip executive-summary-strip"'))
        self.assertIn('id="cockpitCriticalNotifications"', index)
        self.assertIn('id="cockpitInformationalNotifications"', index)
        for section in ("budget", "debts", "top-expenses", "top-income"):
            self.assertIn(f'data-cockpit-section="{section}"', index)
        self.assertIn("Orçamento do mês", index)
        self.assertIn("Ver Limites", index)
        self.assertIn("cockpit-core-grid", index)
        self.assertIn("cockpit-portfolio-panel", index)
        self.assertIn("renderCockpitSummary", cockpit)
        self.assertIn("renderCompactHealth", cockpit)
        self.assertIn(".dashboard-main:has(#cockpitView:not([hidden])) > .topbar", styles)
        self.assertIn("#cockpitView .cockpit-toolbar", styles)
        self.assertIn("background: var(--bg);", styles)
        self.assertNotIn("#cockpitView .cockpit-toolbar {\n  position: sticky;\n  top: 72px", styles)
        self.assertIn("box-shadow: 0 8px 0 var(--bg)", styles)
        self.assertIn("COCKPIT_DISCLOSURE_KEY", cockpit)
        self.assertIn("localStorage.setItem(COCKPIT_DISCLOSURE_KEY", cockpit)

    def test_sidebar_exposes_three_zones_and_reduced_menu_scroll_contract(self) -> None:
        index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")

        self.assertIn('<div class="app-nav-main">', index)
        self.assertIn('<div class="app-nav-utility" aria-label="Utilidades do usuário">', index)
        self.assertLess(index.index('class="app-nav-main"'), index.index('class="app-nav-utility"'))
        self.assertIn('title="Preferências"', index)
        self.assertIn('title="Recolher menu"', index)

        premium_nav = styles[styles.index("/* Design system v4.5") :]
        self.assertIn("overflow: visible", premium_nav)
        self.assertIn("grid-template-rows: minmax(0, 1fr) auto", premium_nav)
        self.assertIn(".nav-button:focus-visible", premium_nav)
        self.assertIn("border-color: var(--focus-border-soft)", premium_nav)

    def test_compact_desktop_adapts_sidebar_header_and_content_grid(self) -> None:
        app_source = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")

        self.assertIn('matchMedia("(max-width: 1180px)")', app_source)
        self.assertIn('compactDesktopQuery.addEventListener("change"', app_source)
        compact = styles[styles.index('/* Desktop compacto:'):]
        self.assertIn("grid-template-columns: 76px minmax(0, 1fr)", compact)
        self.assertIn("grid-template-columns: repeat(2, minmax(0, 1fr))", compact)
        self.assertIn("flex-wrap: wrap", compact)
        self.assertIn("min-width: min(240px, 26vw)", compact)

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

    def test_input_masks_are_applied_to_money_and_date_fields(self) -> None:
        import re

        index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        app_source = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
        mask_source = (MODULE_ROOT / "input-mask.js").read_text(encoding="utf-8")

        self.assertIn('src="/vendor/imask/7.6.1/imask.min.js', index)
        money_inputs = (
            ("amount", False),
            ("investment_amount", False),
            ("investment_unit_price", False),
            ("investment_brokerage_fee", False),
            ("investment_exchange_fee", False),
            ("investment_tax", False),
            ("investment_other_costs", False),
            ("destination_amount", False),
            ("transfer_exchange_rate", False),
            ("limit_amount", False),
            ("total_cost", False),
            ("unit_price", False),
        )
        for name, _ in money_inputs:
            match = re.search(rf'<input[^>]*name="{re.escape(name)}"[^>]*>', index)
            self.assertIsNotNone(match, name)
            self.assertIn('data-mask="money"', match.group(0), name)

        self.assertIn('data-mask="money" data-mask-scale="6" data-mask-signed="false"', index)
        self.assertIn('data-mask="money" data-mask-scale="4" data-mask-signed="false"', index)
        self.assertIn('applyMasks();', app_source)
        self.assertIn('destroyMasks();', app_source)
        self.assertIn('applyMoneyMask', mask_source)
        self.assertIn('applyDateMask', mask_source)
        self.assertIn('thousandsSeparator: "."', mask_source)
        self.assertIn('radix: ","', mask_source)

    def test_command_palette_is_registered_and_accessible(self) -> None:
        import re

        index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        app_source = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
        palette_source = (MODULE_ROOT / "command-palette.js").read_text(encoding="utf-8")
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")

        self.assertIn('id="commandPaletteDialog"', index)
        self.assertIn('id="commandPaletteInput"', index)
        self.assertIn('id="commandPaletteResults"', index)
        self.assertIn('id="commandPaletteTrigger"', index)
        dialog_tag = index[index.index('id="commandPaletteDialog"') - 40:index.index('id="commandPaletteDialog"')]
        self.assertIn('<dialog', dialog_tag)
        self.assertIn('aria-controls="commandPaletteDialog"', index[index.index('id="commandPaletteTrigger"'):index.index('id="commandPaletteTrigger"') + 160])
        self.assertIn('registerCommandPalette', app_source)
        self.assertIn('commandPaletteTrigger?.click()', app_source)
        self.assertIn('event.key.toLowerCase() === "k"', app_source)
        self.assertIn('.command-palette-dialog', styles)
        self.assertIn('.command-palette-results', styles)
        self.assertIn('role="listbox"', index[index.index('id="commandPaletteResults"'):index.index('id="commandPaletteResults"') + 120])
        self.assertIn('aria-activedescendant', palette_source)
        self.assertIn('data-command-palette-index', palette_source)

    def test_virtualization_is_used_for_card_invoices_and_operation_history(self) -> None:
        cards_source = (MODULE_ROOT / "cards-view.js").read_text(encoding="utf-8")
        history_source = (MODULE_ROOT / "operation-history-view.js").read_text(encoding="utf-8")
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")

        virtual_list_source = (MODULE_ROOT / "virtual-list.js").read_text(encoding="utf-8")
        self.assertIn('import { renderCollectionRows } from "./virtual-list.js"', cards_source)
        self.assertIn('import { destroyVirtualLists, renderCollectionRows } from "./virtual-list.js"', history_source)
        self.assertIn("renderCollectionRows(transactionsContainer", cards_source)
        self.assertIn("renderCollectionRows(operationHistoryList", history_source)
        self.assertIn(".card-invoice-transactions.virtual-list", styles)
        self.assertIn(".operation-history-list.virtual-list", styles)
        self.assertIn("aria-rowcount", virtual_list_source)
        self.assertIn("aria-rowindex", virtual_list_source)

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

    def test_account_and_card_launches_share_premium_content_grammar(self) -> None:
        index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")

        self.assertEqual(index.count("launch-section-heading"), 3)
        for shared_class in ("launch-form-drawer", "launch-filter-toolbar"):
            self.assertGreaterEqual(index.count(shared_class), 2, shared_class)
            self.assertIn(f".{shared_class}", styles)
        self.assertIn(".launch-section-heading", styles)
        self.assertIn("launch-form-drawer-header", index)
        self.assertIn("launch-form-drawer-body", index)
        self.assertIn("launch-context-toolbar", index)
        self.assertIn('class="transaction-search launch-context-field"', index)
        account_selector = '<select name="account_id" id="transactionAccount" form="transactionForm" required></select>'
        self.assertIn(account_selector, index)
        account_drawer_start = index.index('id="transactionFormDrawer"')
        account_drawer_end = index.index("</aside>", account_drawer_start)
        self.assertNotIn(account_selector, index[account_drawer_start:account_drawer_end])
        card_drawer_start = index.index('id="cardTransactionFormDrawer"')
        card_drawer_end = index.index("</aside>", card_drawer_start)
        self.assertNotIn('id="cardInvoiceCard"', index[card_drawer_start:card_drawer_end])
        self.assertIn('width: min(760px, calc(100vw - 20px));', styles)
        self.assertIn("#cardLaunchesView .card-invoice-summary > div", styles)
        self.assertIn("#transactionsView .month-balance-summary > div", styles)
        self.assertIn("#cardLaunchesView .card-invoice-row", styles)
        self.assertIn("#transactionsView .transaction-row", styles)

    def test_unclassified_report_review_is_a_global_monthly_destination(self) -> None:
        index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        app = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
        reports = (MODULE_ROOT / "reports-view.js").read_text(encoding="utf-8")

        self.assertIn('data-report-tab="unclassified"', index)
        self.assertIn('"unclassified"]', app)
        self.assertIn('state.reportTab === "unclassified"', reports)
        self.assertIn("Lançamentos sem classificação", reports)
        self.assertIn("reconciledAt", reports)

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

    def test_global_tabs_share_light_surface_language(self) -> None:
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")

        self.assertIn("Design system v5.18 — abas globais", styles)
        self.assertIn("border: 1px solid var(--content-line);", styles)
        self.assertIn("box-shadow: inset 0 -2px 0 var(--accent), var(--content-shadow);", styles)
        self.assertIn(".trends-tabs", styles)
        self.assertIn(".portfolio-tabs", styles)
        self.assertIn(".report-tabs", styles)
        self.assertIn(".notification-flyout-tabs", styles)
        self.assertIn(".notification-flyout-tab[aria-selected=\"true\"]", styles)

    def test_cockpit_consultor_and_health_share_editorial_shell(self) -> None:
        index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")
        consultor = (MODULE_ROOT / "consultor-view.js").read_text(encoding="utf-8")
        health = (MODULE_ROOT / "financial-health-view.js").read_text(encoding="utf-8")

        self.assertIn('class="panel cockpit-calendar-panel cockpit-analysis-panel cockpit-tab-panel"', index)
        self.assertIn('class="panel financial-health-panel cockpit-analysis-panel cockpit-tab-panel"', index)
        self.assertIn('class="cockpit-calendar-header cockpit-analysis-header"', index)
        self.assertIn('class="financial-health-header cockpit-analysis-header"', index)
        self.assertIn('<span class="eyebrow">CONSULTOR</span>', index)
        self.assertIn('<span class="eyebrow">DIAGNÓSTICO</span>', index)
        self.assertIn(".cockpit-analysis-panel {", styles)
        self.assertIn(".cockpit-analysis-header {", styles)
        self.assertIn(".cockpit-calendar-panel .consultor-workspace {", styles)
        self.assertIn(".financial-health-panel .financial-health-content {", styles)
        self.assertIn("bindRovingTablist", consultor)
        self.assertIn("financialHealthGauge", health)

    def test_consultor_history_uses_the_same_editorial_shell(self) -> None:
        index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")

        self.assertIn('class="consultor-history-heading"', index)
        self.assertIn('<span class="eyebrow">CONSULTOR</span>', index)
        self.assertIn('class="consultor-history-filter"', index)
        self.assertIn(".consultor-history-heading {", styles)
        self.assertIn(".cockpit-calendar-panel .consultor-history-list {", styles)
        self.assertIn("background: var(--content-surface-hover);", styles)

    def test_limits_and_reports_use_editorial_states_and_compact_reflow(self) -> None:
        index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")

        for expected in (
            'class="module-editorial-header limits-page-intro"',
            'class="module-editorial-header reports-page-intro"',
            'class="panel limits-overview-panel"',
            'class="panel limits-list-panel"',
            'class="panel reports-overview-panel"',
        ):
            self.assertIn(expected, index)
        self.assertIn("Design system v5.28 — Limites e Relatórios", styles)
        self.assertIn("#limitsView .spending-limit-item", styles)
        self.assertIn("#reportsView .report-rank-row", styles)
        self.assertIn("#reportsView .statement-controls", styles)
        self.assertIn("min-width: 680px", styles)

    def test_limits_form_uses_transaction_style_flyover_and_two_column_list(self) -> None:
        index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")

        self.assertIn('id="limitFormDrawer" class="drawer limit-form-drawer"', index)
        self.assertIn('id="openLimitFormButton"', index)
        self.assertIn('class="limit-form-field-wide"', index)
        self.assertNotIn('class="panel limits-editor-panel"', index)
        self.assertIn(".limit-form-drawer .drawer-content", styles)
        self.assertIn("#limitsView .spending-limit-list", styles)
        self.assertIn("grid-template-columns: repeat(2, minmax(0, 1fr));", styles)
        self.assertIn("#limitsView .limits-workspace {\n  align-items: stretch;", styles)
        self.assertIn("#limitsView .limits-list-panel {\n  align-self: stretch;", styles)

    def test_overlays_share_theme_surface_language(self) -> None:
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")

        self.assertIn("Design system v5.19 — superfícies de flyovers", styles)
        self.assertIn(
            ":is(.drawer-content, .subscription-flyover, .notification-flyout, .global-search-dialog, .command-palette-dialog, .decision-modal)",
            styles,
        )
        self.assertIn("background: var(--content-surface);", styles)
        self.assertIn(".notification-flyout-header,\n.notification-flyout-tabs,\n.notification-flyout-footer", styles)

    def test_goals_share_limits_flyover_and_full_width_list_layout(self) -> None:
        index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")
        limits = (MODULE_ROOT / "limits-view.js").read_text(encoding="utf-8")

        self.assertIn('id="goalFormDrawer" class="drawer goal-form-drawer"', index)
        self.assertIn('id="closeGoalFormButton"', index)
        self.assertIn('aria-controls="goalFormDrawer"', index)
        self.assertNotIn('id="goalFormPanel"', index)
        self.assertIn("goalFormDrawerController?.open()", limits)
        self.assertIn(".goal-form-drawer .drawer-content", styles)
        self.assertIn("#financialGoalsPanel .goals-workspace", styles)
        self.assertIn("#financialGoalsPanel .financial-goal-list", styles)

    def test_currency_balances_keep_numeric_values_clear_of_frame(self) -> None:
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")

        self.assertIn(".currency-section-header {", styles)
        self.assertIn("padding: 14px 18px;", styles)
        self.assertIn("padding: 11px 18px;", styles)
        self.assertIn("overflow-x: hidden;", styles)
        self.assertIn("grid-template-columns: minmax(0, 1.5fr) minmax(80px, 0.8fr) minmax(108px, auto);", styles)
        self.assertIn("min-width: 0;", styles)
        self.assertIn(".currency-table-row strong {\n  padding-inline-start: 6px;", styles)
        self.assertIn("padding: 10px 18px;", styles)

    def test_global_search_is_bounded_keyboard_accessible_and_preserves_view_context(self) -> None:
        index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        app_source = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
        search_source = (MODULE_ROOT / "global-search.js").read_text(encoding="utf-8")

        self.assertIn('id="globalSearchDialog"', index)
        self.assertIn('role="dialog" aria-modal="true"', index)
        self.assertIn('aria-describedby="globalSearchDescription"', index)
        self.assertIn('id="globalSearchInput" type="search"', index)
        self.assertIn('aria-controls="globalSearchResults"', index)
        self.assertIn('role="listbox"', index)
        self.assertIn('event.key === "/"', search_source)
        self.assertIn('!trigger.closest("[hidden]")', search_source)
        self.assertNotIn("state.transactions || []", search_source)
        self.assertNotIn("state.cardTransactions || []", search_source)
        self.assertIn("state.portfolio?.positions || []", search_source)
        self.assertNotIn("fetch(", search_source)
        self.assertIn("/api/global-search?", search_source)
        self.assertIn("requestRevision", search_source)
        self.assertIn("handleDialogKeydown", search_source)
        self.assertIn("previouslyFocused", search_source)
        self.assertIn('event.key !== "Tab"', search_source)
        self.assertIn("setTimeout(async () =>", search_source)
        self.assertIn("const viewScrollPositions = new Map()", app_source)
        self.assertIn("viewScrollPositions.set(previousView, window.scrollY)", app_source)
        self.assertIn("window.scrollTo({ top: viewScrollPositions.get(view) || 0", app_source)

    def test_density_preference_is_local_persistent_and_layout_safe(self) -> None:
        index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        theme_init = (WEB_ROOT / "theme-init.js").read_text(encoding="utf-8")
        app_source = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")
        density_utils = (MODULE_ROOT / "density-utils.js").read_text(encoding="utf-8")
        user_admin = (MODULE_ROOT / "user-admin-view.js").read_text(encoding="utf-8")

        self.assertIn('localStorage.getItem("sistemaFinanceiro.density")', theme_init)
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
        portfolio_form = (MODULE_ROOT / "portfolio-form.js").read_text(encoding="utf-8")
        portfolio_lifecycle = (MODULE_ROOT / "portfolio-lifecycle.js").read_text(encoding="utf-8")
        transactions = (MODULE_ROOT / "transactions-view.js").read_text(encoding="utf-8")
        asset_autocomplete = (MODULE_ROOT / "asset-autocomplete.js").read_text(encoding="utf-8")
        self.assertIn("data-restore-automatic-quote-payload", portfolio)
        self.assertIn('method: "DELETE"', portfolio)
        self.assertIn('triggerButton.textContent = "Atualizando..."', portfolio)
        self.assertIn('quoteCell?.setAttribute("aria-busy", "true")', portfolio)
        self.assertIn("!options.revalidate", portfolio_lifecycle)
        self.assertIn("portfolioView.onEnter()", app_source)
        self.assertIn("loadPortfolio({ revalidate: true, renderCached: false })", portfolio)
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
        self.assertIn("quantity: position.redemption_quantity || position.quantity || 0", portfolio_form)
        self.assertIn("portfolio.redemption_history || []", portfolio)
        self.assertIn("Ganho/perda", portfolio)
        self.assertIn("Custo FIFO", portfolio)
        self.assertIn("redemption.asset_identifier || redemption.asset_type_label", portfolio)
        self.assertIn(".portfolio-col-quantity", styles)
        self.assertIn("width: 118px", styles)
        self.assertIn("state.portfolio.presentation.allocation", portfolio)
        self.assertIn("/api/portfolio/allocation-goals", portfolio)
        self.assertIn('data-portfolio-tab="goals"', index)
        self.assertIn('id="portfolioGoalsForm"', index)
        self.assertRegex(app_source, r'portfolio-view\.js\?v=\d+')
        transition_start = portfolio.index("transitionView(() => {")
        transition_end = portfolio.index("  };", transition_start)
        self.assertIn("renderActivePortfolioTab();", portfolio[transition_start:transition_end])

    def test_loan_study_exposes_optional_gross_cdi_comparison_and_limitations(self) -> None:
        index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        loans = (MODULE_ROOT / "loans-view.js").read_text(encoding="utf-8")
        instructions = (MODULE_ROOT / "instructions-content.js").read_text(encoding="utf-8")

        self.assertIn('id="loanCdiComparisonFields"', index)
        self.assertIn('name="compare_cdi" type="checkbox"', index)
        self.assertIn('id="loanStudyActionFields"', index)
        self.assertIn('name="loan_study_type" type="radio" value="payoff"', index)
        self.assertIn('id="loanAmortizeStudyFields" hidden', index)
        self.assertIn('study_type: studyType', loans)
        self.assertIn('Estudo: quitar ou investir', loans)
        self.assertIn('compare_cdi: studyType === "payoff" || Boolean(formData.get("compare_cdi"))', loans)
        self.assertIn("cdiComparisonMetrics(result.cdi_comparison, loan.currency)", loans)
        self.assertIn("taxa CDI diária mais recente publicada", index)
        self.assertIn("cenário hipotético, não uma previsão", index)
        self.assertIn("O comparativo CDI é bruto", instructions)
        self.assertIn("sem recomendar automaticamente quitar ou investir", instructions)

    def test_import_review_displays_contextual_learned_adjustments(self) -> None:
        index = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        imports = (MODULE_ROOT / "imports-view.js").read_text(encoding="utf-8")
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")

        self.assertIn('id="importSource"', index)
        self.assertIn('value="legacy">Planilha externa (.xls/.csv)', index)
        self.assertIn('value="ofx">Extrato bancário OFX', index)
        self.assertIn("Ajustado nesta revisão", imports)
        self.assertIn("Já ajustado", imports)
        self.assertIn("edited_fields: row.editedFields || []", imports)
        self.assertIn('data-field="categoria"', imports)
        self.assertIn('data-field="subcategoria"', imports)
        self.assertIn('data-field="tags" list="${tagListId}"', imports)
        self.assertIn('descricao_original: "Descrição do arquivo (original)"', imports)
        self.assertIn('value="${escapeHtml(value || "")}" readonly aria-readonly="true"', imports)
        self.assertIn('descricao: "Descrição Lançamento"', imports)
        self.assertIn("function normalizePreviewValues(row)", imports)
        self.assertIn("row.raw?.description", imports)
        self.assertIn('querySelectorAll("[data-field]")', imports)
        self.assertIn("classification_options", imports)
        self.assertIn('value="replace"', imports)
        self.assertIn("data-duplicate-target", imports)
        self.assertIn('data-preview-action', imports)
        self.assertIn("Substituir campos do lançamento existente", imports)
        self.assertIn(".import-preview-duplicate", styles)
        self.assertIn(".import-preview-adjustment", styles)

    def test_import_result_lists_every_row_in_a_compact_single_line(self) -> None:
        imports = (MODULE_ROOT / "imports-view.js").read_text(encoding="utf-8")
        styles = (WEB_ROOT / "styles.css").read_text(encoding="utf-8")

        self.assertIn("const importedRows = (result.rows || []).map", imports)
        self.assertIn("const skippedRows = errors.map", imports)
        self.assertIn("const rowResults = [...importedRows, ...skippedRows]", imports)
        self.assertIn('class="import-result-list"', imports)
        self.assertIn('class="import-result-list__status"', imports)
        self.assertIn("grid-template-columns: auto minmax(100px, 0.8fr) auto minmax(120px, 1.2fr)", styles)
        self.assertIn("white-space: nowrap", styles)


if __name__ == "__main__":
    unittest.main()
