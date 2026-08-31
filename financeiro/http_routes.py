from __future__ import annotations

from collections.abc import Callable


RoutePredicate = Callable[[str], bool]


EXACT_ROUTES: dict[str, dict[str, str]] = {
    "GET": {
        "/api/app-info": "handle_app_info",
        "/api/latest-version": "handle_latest_version",
        "/api/me": "handle_me",
        "/api/checking-accounts": "handle_list_accounts",
        "/api/credit-cards": "handle_list_credit_cards",
        "/api/credit-card-invoice": "handle_list_credit_card_invoice",
        "/api/credit-card-transactions": "handle_list_credit_card_transactions",
        "/api/credit-card-payments": "handle_list_credit_card_payments",
        "/api/transactions": "handle_list_transactions",
        "/api/balance-projection": "handle_balance_projection",
        "/api/exchange-rate": "handle_exchange_rate",
        "/api/classification-suggestion": "handle_classification_suggestion",
        "/api/email-config": "handle_email_config_status",
        "/api/import/template": "handle_import_template_download",
        "/api/categories": "handle_list_categories",
        "/api/tags": "handle_list_tags",
        "/api/spending-limits": "handle_list_spending_limits",
        "/api/cockpit": "handle_cockpit",
        "/api/cockpit/calendar": "handle_cockpit_calendar",
        "/api/financial-health-score": "handle_financial_health_score",
        "/api/financial-health-score/history": "handle_financial_health_score_history",
        "/api/financial-health-trends": "handle_financial_health_trends",
        "/api/ai-settings": "handle_ai_settings_status",
        "/api/mais-retorno-config": "handle_mais_retorno_config_status",
        "/api/consultor/config": "handle_consultor_config",
        "/api/consultor/perfil-complementar": "handle_consultor_complementary_profile",
        "/api/consultor/history": "handle_consultor_history",
        "/api/portfolio": "handle_portfolio",
        "/api/portfolio/returns": "handle_portfolio_returns",
        "/api/portfolio/fund-quote": "handle_portfolio_fund_quote",
        "/api/reports/tags": "handle_tag_report",
        "/api/reports/category-evolution": "handle_category_evolution",
        "/api/operation-logs": "handle_list_operation_logs",
    },
    "POST": {
        "/api/register": "handle_register", "/api/login": "handle_login",
        "/api/password-reset/request": "handle_password_reset_request",
        "/api/password-reset/confirm": "handle_password_reset_confirm",
        "/api/logout": "handle_logout", "/api/me/email": "handle_update_email",
        "/api/me/password": "handle_update_password", "/api/me/clear-launches": "handle_clear_launches",
        "/api/email-config": "handle_save_email_config", "/api/checking-accounts": "handle_create_account",
        "/api/credit-cards": "handle_create_credit_card",
        "/api/credit-card-transactions": "handle_create_credit_card_transaction",
        "/api/credit-card-invoice/pay": "handle_pay_credit_card_invoice",
        "/api/transactions": "handle_create_transaction", "/api/portfolio/positions": "handle_create_portfolio_position",
        "/api/portfolio/redeem": "handle_redeem_portfolio_position", "/api/portfolio/close": "handle_close_portfolio_position",
        "/api/import/legacy-transactions": "handle_import_legacy_transactions",
        "/api/import/system-template": "handle_import_system_template", "/api/categories": "handle_create_category",
        "/api/subcategories": "handle_create_subcategory", "/api/tags": "handle_create_tag",
        "/api/spending-limits": "handle_create_spending_limit",
        "/api/simulations/butterfly-effect": "handle_simulate_butterfly_effect",
        "/api/financial-health-trends/ai-summary": "handle_ai_summary",
        "/api/consultor/config": "handle_save_consultor_config",
        "/api/consultor/perfil-complementar": "handle_save_consultor_complementary_profile",
        "/api/consultor/analyze": "handle_consultor_analyze",
    },
    "PUT": {
        "/api/portfolio/value": "handle_update_portfolio_value",
        "/api/portfolio/allocation-goals": "handle_save_portfolio_allocation_goals",
        "/api/ai-settings": "handle_save_ai_settings", "/api/mais-retorno-config": "handle_save_mais_retorno_config",
    },
    "DELETE": {
        "/api/me": "handle_delete_user", "/api/portfolio/value": "handle_delete_portfolio_value_override",
        "/api/consultor/perfil-complementar": "handle_delete_consultor_complementary_profile",
        "/api/consultor/history": "handle_delete_consultor_history",
    },
}


PATTERN_ROUTES: dict[str, tuple[tuple[RoutePredicate, str], ...]] = {
    "GET": ((lambda path: path.startswith("/api/operation-logs/"), "handle_operation_log_detail"),),
    "POST": (
        (lambda path: path.startswith("/api/checking-accounts/") and path.endswith("/restore"), "handle_restore_account"),
        (lambda path: path.startswith("/api/credit-cards/") and path.endswith("/restore"), "handle_restore_credit_card"),
    ),
    "PUT": (
        (lambda path: path.startswith("/api/transactions/") and path.endswith("/reconciliation"), "handle_reconcile_transaction"),
        (lambda path: path.startswith("/api/credit-card-transactions/") and path.endswith("/reconciliation"), "handle_reconcile_credit_card_transaction"),
        (lambda path: path.startswith("/api/credit-card-transactions/") and path.endswith("/invoice"), "handle_move_credit_card_transaction_invoice"),
        (lambda path: path.startswith("/api/credit-card-transactions/"), "handle_update_credit_card_transaction"),
        (lambda path: path.startswith("/api/transactions/"), "handle_update_transaction"),
        (lambda path: path.startswith("/api/portfolio/positions/"), "handle_update_portfolio_position"),
        (lambda path: path.startswith("/api/checking-accounts/"), "handle_update_account"),
        (lambda path: path.startswith("/api/credit-cards/"), "handle_update_credit_card"),
        (lambda path: path.startswith("/api/categories/"), "handle_update_category"),
        (lambda path: path.startswith("/api/subcategories/"), "handle_update_subcategory"),
        (lambda path: path.startswith("/api/tags/"), "handle_update_tag"),
        (lambda path: path.startswith("/api/spending-limits/"), "handle_update_spending_limit"),
    ),
    "DELETE": (),
}

PATTERN_ROUTES["DELETE"] = tuple(
    ((lambda prefix: (lambda path: path.startswith(prefix)))(prefix), handler)
    for prefix, handler in (
        ("/api/categories/", "handle_delete_category"), ("/api/subcategories/", "handle_delete_subcategory"),
        ("/api/tags/", "handle_delete_tag"), ("/api/spending-limits/", "handle_delete_spending_limit"),
        ("/api/portfolio/positions/", "handle_delete_portfolio_position"),
        ("/api/checking-accounts/", "handle_archive_account"), ("/api/credit-cards/", "handle_archive_credit_card"),
        ("/api/credit-card-transactions/", "handle_delete_credit_card_transaction"),
        ("/api/transactions/", "handle_delete_transaction"),
    )
)


def resolve_route(method: str, path: str) -> str | None:
    handler = EXACT_ROUTES.get(method, {}).get(path)
    if handler:
        return handler
    for predicate, candidate in PATTERN_ROUTES.get(method, ()):
        if predicate(path):
            return candidate
    return None


def dispatch_route(target: object, method: str, path: str) -> bool:
    handler_name = resolve_route(method, path)
    if not handler_name:
        return False
    getattr(target, handler_name)()
    return True
