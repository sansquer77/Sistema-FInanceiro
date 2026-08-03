from __future__ import annotations

import json
import mimetypes
import os
import re
import sqlite3
import sys
from datetime import date
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from urllib.parse import parse_qs
import ipaddress

from financeiro.accounts import (
    archive_checking_account,
    create_checking_account,
    list_archived_checking_accounts,
    list_checking_accounts,
    restore_checking_account,
    update_checking_account,
)
from financeiro.app_metadata import APP_NAME, APP_VERSION, app_info
from financeiro.auth import (
    clear_user_launches,
    create_session,
    create_user,
    delete_user_account,
    get_current_user,
    login_user,
    logout_session,
    request_password_reset,
    reset_password,
    update_user_email,
    update_user_password,
)
from financeiro.categories import (
    create_category,
    create_subcategory,
    create_tag,
    delete_category,
    delete_subcategory,
    delete_tag,
    list_categories,
    list_tags,
    update_category,
    update_subcategory,
    update_tag,
    get_category_evolution,
)
from financeiro.classification_suggestions import get_classification_suggestion
from financeiro.credit_cards import (
    archive_credit_card,
    create_credit_card,
    create_credit_card_transaction,
    delete_credit_card_transaction,
    fetch_card_transaction,
    format_card_transaction,
    list_archived_credit_cards,
    list_credit_card_invoice,
    list_credit_card_payments,
    list_credit_card_transactions,
    list_credit_cards,
    move_credit_card_transaction_invoice,
    pay_credit_card_invoice,
    restore_credit_card,
    set_credit_card_transaction_reconciled,
    update_credit_card_transaction,
    update_credit_card,
)
from financeiro.database import initialize_database
from financeiro.database import get_connection
from financeiro.ai_summary import ai_summary_enabled, generate_ai_summary
from financeiro.financial_health import (
    FinancialHealthError,
    calculate_financial_health_score,
    calculate_financial_health_score_history,
)
from financeiro.imports import import_organizze_transactions, import_system_template, system_import_template
from financeiro.operation_logs import create_operation_log, get_operation_log, list_operation_logs
from financeiro.portfolio import close_position, create_opening_position, delete_opening_position, get_portfolio, redeem_position, update_opening_position, update_position_value_override
from financeiro.secure_config import (
    SecureConfigError,
    ai_settings_status,
    email_config_status,
    save_ai_settings,
    save_email_config,
)
from financeiro.simulations import simulate_butterfly_effect
from financeiro.trends import TrendsError, calculate_trends
from financeiro.spending_limits import (
    create_spending_limit,
    delete_spending_limit,
    list_spending_limits,
    update_spending_limit,
)
from financeiro.transactions import (
    create_transaction,
    delete_transaction,
    fetch_transaction,
    format_transaction,
    get_exchange_rate_to_brl,
    list_transactions,
    set_transaction_reconciled,
    update_transaction,
)

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
WEB_ROOT = ROOT / "web"
HOST = os.environ.get("APP_HOST", "127.0.0.1")
PORT = int(os.environ.get("APP_PORT", "8010"))
PUBLIC_URL = os.environ.get("APP_URL", f"http://sistema-financeiro.localhost:{PORT}")
LOCAL_ALLOWED_HOSTS = frozenset({"sistema-financeiro.localhost", "127.0.0.1"})
DEFAULT_ALLOWED_HOSTS = frozenset({
    "sistema-financeiro.net",
    "sistema-financeiro.net:8030",
    "192.168.1.212",
    "192.168.1.212:8030",
})
DEFAULT_ALLOWED_ORIGINS = frozenset({
    "http://sistema-financeiro.localhost:8010",
    "https://sistema-financeiro.net:8030",
    "http://sistema-financeiro.net:8030",
    "https://192.168.1.212:8030",
    "http://192.168.1.212:8030",
})
MAX_JSON_BODY_BYTES = 1 * 1024 * 1024
SESSION_COOKIE_MAX_AGE_SECONDS = 30 * 24 * 60 * 60
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "font-src 'self' data:; "
        "connect-src 'self'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'; "
        "object-src 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


def normalize_netloc(value: str) -> str:
    parsed = urlsplit(f"//{value.strip().lower()}")
    host = (parsed.hostname or "").rstrip(".")
    if not host:
        return ""
    try:
        port = parsed.port
    except ValueError:
        return ""
    if port is None:
        return host
    return f"{host}:{port}"


def csv_env_values(name: str) -> list[str]:
    return [value.strip() for value in os.environ.get(name, "").split(",") if value.strip()]


def host_variants(value: str) -> set[str]:
    normalized = normalize_netloc(value)
    if not normalized:
        return set()
    if ":" in normalized:
        return {normalized}
    return {normalized, f"{normalized}:{PORT}"}


def normalize_origin(value: str) -> str:
    candidate = value.strip()
    if not candidate:
        return ""
    if "://" not in candidate:
        candidate = f"http://{candidate}"
    parsed = urlsplit(candidate)
    if not parsed.scheme or not parsed.netloc:
        return ""
    netloc = normalize_netloc(parsed.netloc)
    if not netloc:
        return ""
    if ":" not in netloc:
        netloc = f"{netloc}:{PORT}"
    return f"{parsed.scheme.lower()}://{netloc}"


def public_url_origin() -> str:
    public_url = urlsplit(PUBLIC_URL)
    if not public_url.scheme or not public_url.netloc:
        return ""
    return f"{public_url.scheme.lower()}://{normalize_netloc(public_url.netloc)}"


def allowed_host_values() -> set[str]:
    hosts = {f"{host}:{PORT}" for host in LOCAL_ALLOWED_HOSTS}
    for value in DEFAULT_ALLOWED_HOSTS:
        hosts.update(host_variants(value))
    for value in csv_env_values("APP_ALLOWED_HOSTS"):
        hosts.update(host_variants(value))
    public_host = normalize_netloc(urlsplit(PUBLIC_URL).netloc)
    if public_host:
        hosts.update(host_variants(public_host))
    return hosts


def allowed_origin_values() -> set[str]:
    origins = {f"http://{host}:{PORT}" for host in LOCAL_ALLOWED_HOSTS}
    origins.update(DEFAULT_ALLOWED_ORIGINS)
    for value in csv_env_values("APP_ALLOWED_ORIGINS"):
        origin = normalize_origin(value)
        if origin:
            origins.add(origin)
    public_origin = public_url_origin()
    if public_origin:
        origins.add(public_origin)
    return origins


class AppHandler(BaseHTTPRequestHandler):
    server_version = f"{APP_NAME.replace(' ', '')}/{APP_VERSION}"

    def do_GET(self) -> None:
        path = self.route_path()
        if path == "/api/app-info":
            self.handle_app_info()
            return
        if path.startswith("/api/me"):
            self.handle_me()
            return
        if path.startswith("/api/checking-accounts"):
            self.handle_list_accounts()
            return
        if path.startswith("/api/credit-cards"):
            self.handle_list_credit_cards()
            return
        if path == "/api/credit-card-invoice":
            self.handle_list_credit_card_invoice()
            return
        if path == "/api/credit-card-transactions":
            self.handle_list_credit_card_transactions()
            return
        if path == "/api/credit-card-payments":
            self.handle_list_credit_card_payments()
            return
        if path.startswith("/api/transactions"):
            self.handle_list_transactions()
            return
        if path == "/api/exchange-rate":
            self.handle_exchange_rate()
            return
        if path == "/api/classification-suggestion":
            self.handle_classification_suggestion()
            return
        if path == "/api/email-config":
            self.handle_email_config_status()
            return
        if path == "/api/import/template":
            self.handle_import_template_download()
            return
        if path == "/api/categories":
            self.handle_list_categories()
            return
        if path == "/api/tags":
            self.handle_list_tags()
            return
        if path == "/api/spending-limits":
            self.handle_list_spending_limits()
            return
        if path == "/api/simulations/butterfly-effect":
            self.send_json({"error": "Metodo nao permitido."}, HTTPStatus.METHOD_NOT_ALLOWED)
            return
        if path == "/api/cockpit":
            self.handle_cockpit()
            return
        if path == "/api/financial-health-score":
            self.handle_financial_health_score()
            return
        if path == "/api/financial-health-score/history":
            self.handle_financial_health_score_history()
            return
        if path == "/api/financial-health-trends":
            self.handle_financial_health_trends()
            return
        if path == "/api/ai-settings":
            self.handle_ai_settings_status()
            return
        if path == "/api/portfolio":
            self.handle_portfolio()
            return
        if path == "/api/reports/category-evolution":
            self.handle_category_evolution()
            return
        if path == "/api/operation-logs":
            self.handle_list_operation_logs()
            return
        if path.startswith("/api/operation-logs/"):
            self.handle_operation_log_detail()
            return
        self.serve_static()

    def do_POST(self) -> None:
        if not self.validate_mutation_source():
            return
        path = self.route_path()
        if path == "/api/register":
            self.handle_register()
            return
        if path == "/api/login":
            self.handle_login()
            return
        if path == "/api/password-reset/request":
            self.handle_password_reset_request()
            return
        if path == "/api/password-reset/confirm":
            self.handle_password_reset_confirm()
            return
        if path == "/api/logout":
            self.handle_logout()
            return
        if path == "/api/me/email":
            self.handle_update_email()
            return
        if path == "/api/me/password":
            self.handle_update_password()
            return
        if path == "/api/me/clear-launches":
            self.handle_clear_launches()
            return
        if path == "/api/email-config":
            self.handle_save_email_config()
            return
        if path.startswith("/api/checking-accounts/") and path.endswith("/restore"):
            self.handle_restore_account()
            return
        if path.startswith("/api/credit-cards/") and path.endswith("/restore"):
            self.handle_restore_credit_card()
            return
        if path == "/api/checking-accounts":
            self.handle_create_account()
            return
        if path == "/api/credit-cards":
            self.handle_create_credit_card()
            return
        if path == "/api/credit-card-transactions":
            self.handle_create_credit_card_transaction()
            return
        if path == "/api/credit-card-invoice/pay":
            self.handle_pay_credit_card_invoice()
            return
        if path == "/api/transactions":
            self.handle_create_transaction()
            return
        if path == "/api/portfolio/positions":
            self.handle_create_portfolio_position()
            return
        if path == "/api/portfolio/redeem":
            self.handle_redeem_portfolio_position()
            return
        if path == "/api/portfolio/close":
            self.handle_close_portfolio_position()
            return
        if path == "/api/import/organizze-transactions":
            self.handle_import_organizze_transactions()
            return
        if path == "/api/import/system-template":
            self.handle_import_system_template()
            return
        if path == "/api/categories":
            self.handle_create_category()
            return
        if path == "/api/subcategories":
            self.handle_create_subcategory()
            return
        if path == "/api/tags":
            self.handle_create_tag()
            return
        if path == "/api/spending-limits":
            self.handle_create_spending_limit()
            return
        if path == "/api/simulations/butterfly-effect":
            self.handle_simulate_butterfly_effect()
            return
        if path == "/api/financial-health-trends/ai-summary":
            self.handle_ai_summary()
            return
        self.send_json({"error": "Rota nao encontrada."}, HTTPStatus.NOT_FOUND)

    def do_PUT(self) -> None:
        if not self.validate_mutation_source():
            return
        path = self.route_path()
        if path.startswith("/api/transactions/") and path.endswith("/reconciliation"):
            self.handle_reconcile_transaction()
            return
        if path.startswith("/api/credit-card-transactions/") and path.endswith("/reconciliation"):
            self.handle_reconcile_credit_card_transaction()
            return
        if path.startswith("/api/credit-card-transactions/") and path.endswith("/invoice"):
            self.handle_move_credit_card_transaction_invoice()
            return
        if path.startswith("/api/credit-card-transactions/"):
            self.handle_update_credit_card_transaction()
            return
        if path.startswith("/api/transactions/"):
            self.handle_update_transaction()
            return
        if path.startswith("/api/portfolio/positions/"):
            self.handle_update_portfolio_position()
            return
        if path == "/api/portfolio/value":
            self.handle_update_portfolio_value()
            return
        if path.startswith("/api/checking-accounts/"):
            self.handle_update_account()
            return
        if path.startswith("/api/credit-cards/"):
            self.handle_update_credit_card()
            return
        if path.startswith("/api/categories/"):
            self.handle_update_category()
            return
        if path.startswith("/api/subcategories/"):
            self.handle_update_subcategory()
            return
        if path.startswith("/api/tags/"):
            self.handle_update_tag()
            return
        if path.startswith("/api/spending-limits/"):
            self.handle_update_spending_limit()
            return
        if path == "/api/ai-settings":
            self.handle_save_ai_settings()
            return
        self.send_json({"error": "Rota nao encontrada."}, HTTPStatus.NOT_FOUND)

    def do_DELETE(self) -> None:
        if not self.validate_mutation_source():
            return
        path = self.route_path()
        if path == "/api/me":
            self.handle_delete_user()
            return
        if path.startswith("/api/categories/"):
            self.handle_delete_category()
            return
        if path.startswith("/api/subcategories/"):
            self.handle_delete_subcategory()
            return
        if path.startswith("/api/tags/"):
            self.handle_delete_tag()
            return
        if path.startswith("/api/spending-limits/"):
            self.handle_delete_spending_limit()
            return
        if path.startswith("/api/portfolio/positions/"):
            self.handle_delete_portfolio_position()
            return
        if path.startswith("/api/checking-accounts/"):
            self.handle_archive_account()
            return
        if path.startswith("/api/credit-cards/"):
            self.handle_archive_credit_card()
            return
        if path.startswith("/api/credit-card-transactions/"):
            self.handle_delete_credit_card_transaction()
            return
        if path.startswith("/api/transactions/"):
            self.handle_delete_transaction()
            return
        self.send_json({"error": "Rota nao encontrada."}, HTTPStatus.NOT_FOUND)

    def route_path(self) -> str:
        path = urlsplit(self.path).path
        if path != "/":
            path = path.rstrip("/")
        return path

    def handle_me(self) -> None:
        user = self.require_user(allow_anonymous=True)
        self.send_json({"user": user})

    def handle_register(self) -> None:
        data = self.read_json()
        user = create_user(data.get("name", ""), data.get("email", ""), data.get("password", ""))
        token = create_session(user["id"])
        self.send_json({"user": user}, headers=self.session_cookie(token), status=HTTPStatus.CREATED)

    def handle_login(self) -> None:
        data = self.read_json()
        user = login_user(data.get("email", ""), data.get("password", ""), source_key=self.client_source_key())
        token = create_session(user["id"])
        self.send_json({"user": user}, headers=self.session_cookie(token))

    def handle_logout(self) -> None:
        token = self.get_cookie("session")
        if token:
            logout_session(token)
        self.send_json({"ok": True}, headers={"Set-Cookie": self.expired_session_cookie()})

    def handle_password_reset_request(self) -> None:
        data = self.read_json()
        result = request_password_reset(data.get("email", ""), source_key=self.client_source_key())
        self.send_json(result)

    def handle_password_reset_confirm(self) -> None:
        data = self.read_json()
        reset_password(data.get("token", ""), data.get("new_password", ""), source_key=self.client_source_key())
        self.send_json({"ok": True})

    def handle_update_email(self) -> None:
        user = self.require_user()
        data = self.read_json()
        updated = update_user_email(user["id"], data.get("email", ""), data.get("current_password", ""))
        self.record_operation(user["id"], "user_admin", "update", "user", "Email do usuario alterado", updated["id"])
        self.send_json({"user": updated})

    def handle_update_password(self) -> None:
        user = self.require_user()
        data = self.read_json()
        update_user_password(user["id"], data.get("current_password", ""), data.get("new_password", ""))
        self.record_operation(user["id"], "user_admin", "update", "user", "Senha do usuario alterada", user["id"])
        self.send_json({"ok": True}, headers={"Set-Cookie": self.expired_session_cookie()})

    def handle_delete_user(self) -> None:
        user = self.require_user()
        data = self.read_json()
        self.record_operation(user["id"], "user_admin", "delete", "user", "Usuario excluido", user["id"])
        delete_user_account(user["id"], data.get("current_password", ""))
        self.send_json({"ok": True}, headers={"Set-Cookie": self.expired_session_cookie()})

    def handle_clear_launches(self) -> None:
        user = self.require_user()
        data = self.read_json()
        clear_user_launches(user["id"], data.get("current_password", ""))
        self.record_operation(user["id"], "user_admin", "clear", "user", "Lancamentos do usuario limpos", user["id"])
        self.send_json({"ok": True})

    def handle_email_config_status(self) -> None:
        user = self.require_user()
        self.send_json(email_config_status(user["id"]))

    def handle_save_email_config(self) -> None:
        user = self.require_user()
        data = self.read_json()
        try:
            self.send_json(save_email_config(user["id"], data))
        except SecureConfigError as exc:
            raise ApiError(str(exc) or "Configuracao de email invalida.") from exc

    def handle_app_info(self) -> None:
        self.send_json(app_info())

    def handle_list_accounts(self) -> None:
        user = self.require_user()
        if "status=archived" in self.path.split("?", 1)[-1]:
            accounts = list_archived_checking_accounts(user["id"])
        else:
            accounts = list_checking_accounts(user["id"])
        self.send_json({"accounts": accounts})

    def handle_list_credit_cards(self) -> None:
        user = self.require_user()
        if "status=archived" in self.path.split("?", 1)[-1]:
            cards = list_archived_credit_cards(user["id"])
        else:
            cards = list_credit_cards(user["id"])
        self.send_json({"cards": cards})

    def handle_list_credit_card_invoice(self) -> None:
        user = self.require_user()
        query = parse_qs(urlsplit(self.path).query)
        card_id = (query.get("card_id") or [""])[0]
        month = (query.get("month") or [""])[0]
        self.send_json(list_credit_card_invoice(user["id"], card_id, month))

    def handle_list_credit_card_transactions(self) -> None:
        user = self.require_user()
        self.send_json({"transactions": list_credit_card_transactions(user["id"])})

    def handle_list_credit_card_payments(self) -> None:
        user = self.require_user()
        self.send_json({"payments": list_credit_card_payments(user["id"])})

    def handle_list_transactions(self) -> None:
        user = self.require_user()
        query = parse_qs(urlsplit(self.path).query)
        month = (query.get("month") or [None])[0]
        account_id = (query.get("account_id") or [None])[0]
        try:
            normalized_account_id = int(account_id) if account_id else None
        except ValueError as exc:
            raise ApiError("Conta invalida.") from exc
        transactions = list_transactions(user["id"], month=month, account_id=normalized_account_id)
        self.send_json({"transactions": transactions})

    def handle_cockpit(self) -> None:
        user = self.require_user()
        query = parse_qs(urlsplit(self.path).query)
        month = (query.get("month") or [date.today().strftime("%Y-%m")])[0]
        transactions = list_transactions(user["id"], month=month)
        card_transactions = list_credit_card_transactions(user["id"], invoice_month=month)
        self.send_json(cockpit_payload([*transactions, *card_transactions]))

    def handle_financial_health_score(self) -> None:
        # spec: score-saude-financeira v2.5 — critério 15
        if not self.validate_read_source():
            return
        user = self.require_user()
        query = parse_qs(urlsplit(self.path).query)
        month = (query.get("month") or [date.today().strftime("%Y-%m")])[0]
        try:
            self.send_json(calculate_financial_health_score(user["id"], month))
        except FinancialHealthError as exc:
            self.send_json({"error": exc.message}, exc.status)

    def handle_financial_health_score_history(self) -> None:
        # spec: score-saude-financeira v2.5 — critérios 16 e 17
        if not self.validate_read_source():
            return
        user = self.require_user()
        query = parse_qs(urlsplit(self.path).query)
        months = (query.get("months") or [None])[0]
        try:
            self.send_json({"history": calculate_financial_health_score_history(user["id"], months)})
        except FinancialHealthError as exc:
            self.send_json({"error": exc.message}, exc.status)

    def handle_financial_health_trends(self) -> None:
        # spec: tendencias-saude-financeira v2.13 — critérios 1, 3, 4, 5, 6, 7, 13, 17, 25, 26, 27 e 28
        if not self.validate_read_source():
            return
        user = self.require_user()
        query = parse_qs(urlsplit(self.path).query)
        month = (query.get("month") or [date.today().strftime("%Y-%m")])[0]
        try:
            payload = calculate_trends(user["id"], month)
            payload["ia_ativa"] = ai_summary_enabled(user["id"])
            self.send_json(payload)
        except TrendsError as exc:
            self.send_json({"error": exc.message}, exc.status)

    def handle_ai_settings_status(self) -> None:
        # spec: tendencias-saude-financeira v2.13 — critérios 17, 18 e 19
        if not self.validate_read_source():
            return
        user = self.require_user()
        self.send_json(ai_settings_status(user["id"]))

    def handle_save_ai_settings(self) -> None:
        # spec: tendencias-saude-financeira v2.13 — critérios 17, 18, 19, 21, 23, 27 e 28
        user = self.require_user()
        data = self.read_json()
        try:
            self.send_json(save_ai_settings(user["id"], data))
        except SecureConfigError as exc:
            self.send_json({"error": str(exc) or "Configuracao de IA invalida."}, HTTPStatus.BAD_REQUEST)

    def handle_ai_summary(self) -> None:
        # spec: tendencias-saude-financeira v2.13 — critérios 12, 13, 14, 16 e 17
        user = self.require_user()
        data = self.read_json()
        month = data.get("month") or date.today().strftime("%Y-%m")
        try:
            trends = calculate_trends(user["id"], month)
        except TrendsError as exc:
            self.send_json({"error": exc.message}, exc.status)
            return
        summary = generate_ai_summary(user["id"], trends)
        self.send_json({
            "resumo_ia": summary,
            "resumo_local": trends["resumo_local"],
            "ia_usada": summary is not None,
        })

    def handle_exchange_rate(self) -> None:
        self.require_user()
        query = parse_qs(urlsplit(self.path).query)
        currency = (query.get("currency") or ["BRL"])[0]
        transaction_date = (query.get("date") or [None])[0]
        rate = get_exchange_rate_to_brl(currency, transaction_date)
        self.send_json({"currency": currency.upper(), "date": transaction_date, "rate": f"{rate:.6f}"})

    def handle_classification_suggestion(self) -> None:
        user = self.require_user()
        query = parse_qs(urlsplit(self.path).query)
        description = (query.get("description") or [""])[0]
        group_type = (query.get("group_type") or [""])[0]
        self.send_json(get_classification_suggestion(user["id"], description, group_type))

    def handle_list_categories(self) -> None:
        user = self.require_user()
        query = parse_qs(urlsplit(self.path).query)
        group_type = (query.get("group") or [None])[0]
        self.send_json({"categories": list_categories(user["id"], group_type)})

    def handle_category_evolution(self) -> None:
        user = self.require_user()
        query = parse_qs(urlsplit(self.path).query)
        category_id_str = (query.get("category_id") or [""])[0]
        subcategory_id_str = (query.get("subcategory_id") or [""])[0]
        period = (query.get("period") or ["12m"])[0]
        
        if not category_id_str.isdigit():
            self.send_error(HTTPStatus.BAD_REQUEST, "ID da categoria invalido.")
            return
            
        category_id = int(category_id_str)
        subcategory_id = int(subcategory_id_str) if subcategory_id_str.isdigit() else None
        
        evolution = get_category_evolution(user["id"], category_id, subcategory_id, period)
        self.send_json({"evolution": evolution})

    def handle_list_tags(self) -> None:
        user = self.require_user()
        self.send_json({"tags": list_tags(user["id"])})

    def handle_list_spending_limits(self) -> None:
        user = self.require_user()
        query = parse_qs(urlsplit(self.path).query)
        month = (query.get("month") or [None])[0]
        self.send_json({"limits": list_spending_limits(user["id"], month)})

    def handle_list_operation_logs(self) -> None:
        user = self.require_user()
        query = parse_qs(urlsplit(self.path).query)
        filters = {key: values[0] for key, values in query.items() if values}
        self.send_json(list_operation_logs(user["id"], filters))

    def handle_operation_log_detail(self) -> None:
        user = self.require_user()
        log_id = self.route_path().rsplit("/", 1)[-1]
        self.send_json({"log": get_operation_log(user["id"], log_id)})

    def handle_simulate_butterfly_effect(self) -> None:
        user = self.require_user()
        data = self.read_json()
        self.send_json(simulate_butterfly_effect(user["id"], data))

    def handle_portfolio(self) -> None:
        user = self.require_user()
        query = parse_qs(urlsplit(self.path).query)
        force_refresh = (query.get("refresh") or [""])[0].lower() in {"1", "true", "yes", "sim"}
        self.send_json(get_portfolio(user["id"], force_refresh=force_refresh))

    def handle_create_portfolio_position(self) -> None:
        user = self.require_user()
        data = self.read_json()
        result = create_opening_position(user["id"], data)
        position = result.get("opening_position") or result.get("position") or {}
        self.record_operation(
            user["id"], "portfolio", "create", "portfolio_position",
            "Posicao de portfolio cadastrada", position.get("id"),
            account_id=position.get("account_id") or data.get("account_id"),
            metadata={"asset_name": data.get("asset_name"), "asset_identifier": data.get("asset_identifier")},
        )
        self.send_json(result, status=HTTPStatus.CREATED)

    def handle_update_portfolio_position(self) -> None:
        user = self.require_user()
        position_id = self.route_path().rsplit("/", 1)[-1]
        data = self.read_json()
        result = update_opening_position(user["id"], position_id, data)
        self.record_operation(
            user["id"], "portfolio", "update", "portfolio_position",
            "Posicao de portfolio atualizada", position_id,
            account_id=data.get("account_id"),
            metadata={"asset_name": data.get("asset_name"), "asset_identifier": data.get("asset_identifier")},
        )
        self.send_json(result)

    def handle_delete_portfolio_position(self) -> None:
        user = self.require_user()
        position_id = self.route_path().rsplit("/", 1)[-1]
        result = delete_opening_position(user["id"], position_id)
        self.record_operation(user["id"], "portfolio", "delete", "portfolio_position", "Posicao de portfolio excluida", position_id)
        self.send_json(result)

    def handle_redeem_portfolio_position(self) -> None:
        user = self.require_user()
        data = self.read_json()
        result = redeem_position(user["id"], data)
        self.record_operation(
            user["id"], "portfolio", "redeem", "portfolio_redemption",
            "Resgate de portfolio registrado", None,
            account_id=data.get("account_id"),
            metadata={"source_type": data.get("source_type"), "source_id": data.get("source_id")},
        )
        self.send_json(result, status=HTTPStatus.CREATED)

    def handle_close_portfolio_position(self) -> None:
        user = self.require_user()
        data = self.read_json()
        result = close_position(user["id"], data)
        self.record_operation(
            user["id"], "portfolio", "close", "portfolio_position",
            "Posicao de portfolio encerrada", None,
            account_id=data.get("account_id"),
            metadata={"asset_type": data.get("asset_type"), "closed_at": data.get("closed_at")},
        )
        self.send_json(result, status=HTTPStatus.CREATED)

    def handle_update_portfolio_value(self) -> None:
        user = self.require_user()
        data = self.read_json()
        result = update_position_value_override(user["id"], data)
        self.record_operation(
            user["id"], "portfolio", "value_update", "portfolio_position",
            "Valor de portfolio atualizado", None,
            account_id=data.get("account_id"),
            metadata={"asset_type": data.get("asset_type"), "quote_date": data.get("quote_date")},
        )
        self.send_json(result)

    def handle_create_account(self) -> None:
        user = self.require_user()
        data = self.read_json()
        account = create_checking_account(user["id"], data)
        self.record_operation(user["id"], "accounts", "create", "account", f"Conta criada: {account['name']}", account["id"], account_id=account["id"], metadata={"currency": account.get("currency")})
        self.send_json({"account": account}, status=HTTPStatus.CREATED)

    def handle_create_credit_card(self) -> None:
        user = self.require_user()
        data = self.read_json()
        card = create_credit_card(user["id"], data)
        self.record_operation(user["id"], "cards", "create", "credit_card", f"Cartao criado: {card['name']}", card["id"], credit_card_id=card["id"], metadata={"currency": card.get("currency")})
        self.send_json({"card": card}, status=HTTPStatus.CREATED)

    def handle_create_credit_card_transaction(self) -> None:
        user = self.require_user()
        data = self.read_json()
        transaction = create_credit_card_transaction(user["id"], data)
        self.record_operation(
            user["id"], "cards", "create", "credit_card_transaction",
            f"Lancamento de cartao criado: {transaction['description']}", transaction["id"],
            credit_card_id=transaction.get("credit_card_id"),
            operation_batch_id=transaction.get("series_id"),
            metadata={"amount": transaction.get("amount"), "invoice_month": transaction.get("invoice_month"), "series_kind": transaction.get("series_kind")},
        )
        self.send_json({"transaction": transaction}, status=HTTPStatus.CREATED)

    def handle_update_credit_card_transaction(self) -> None:
        user = self.require_user()
        transaction_id = self.path.split("?", 1)[0].split("/")[-1]
        data = self.read_json()
        previous = load_card_transaction_snapshot(user["id"], transaction_id)
        transaction = update_credit_card_transaction(user["id"], transaction_id, data)
        metadata = {
            "amount": transaction.get("amount"),
            "invoice_month": transaction.get("invoice_month"),
            **change_metadata(previous, transaction, CARD_TRANSACTION_AUDIT_FIELDS),
        }
        self.record_operation(
            user["id"], "cards", "update", "credit_card_transaction",
            f"Lancamento de cartao atualizado: {transaction['description']}", transaction["id"],
            credit_card_id=transaction.get("credit_card_id"),
            operation_batch_id=transaction.get("series_id") if data.get("scope") == "future" else None,
            metadata=metadata,
        )
        self.send_json({"transaction": transaction})

    def handle_move_credit_card_transaction_invoice(self) -> None:
        user = self.require_user()
        path_parts = self.path.split("?", 1)[0].split("/")
        transaction_id = path_parts[-2]
        data = self.read_json()
        transaction = move_credit_card_transaction_invoice(user["id"], transaction_id, data.get("direction"))
        self.record_operation(
            user["id"], "cards", "move", "credit_card_transaction",
            f"Lancamento movido para fatura {transaction['invoice_month']}", transaction["id"],
            credit_card_id=transaction.get("credit_card_id"),
            metadata={"direction": data.get("direction"), "invoice_month": transaction.get("invoice_month")},
        )
        self.send_json({"transaction": transaction})

    def handle_pay_credit_card_invoice(self) -> None:
        user = self.require_user()
        data = self.read_json()
        result = pay_credit_card_invoice(user["id"], data)
        payment = result.get("payment") or {}
        self.record_operation(
            user["id"], "cards", "pay", "credit_card_payment",
            f"Fatura paga: {data.get('invoice_month', '')}", payment.get("id"),
            account_id=data.get("account_id"),
            credit_card_id=data.get("credit_card_id"),
            metadata={"invoice_month": data.get("invoice_month"), "transaction_id": payment.get("transaction_id")},
        )
        self.send_json(result, status=HTTPStatus.CREATED)

    def handle_create_transaction(self) -> None:
        user = self.require_user()
        data = self.read_json()
        transaction = create_transaction(user["id"], data)
        self.record_operation(
            user["id"], "transactions", "create", "transaction",
            f"Lancamento criado: {transaction['description']}", transaction["id"],
            account_id=transaction.get("account_id"),
            operation_batch_id=transaction.get("series_id"),
            metadata={"amount": transaction.get("amount"), "type": transaction.get("type"), "date": transaction.get("date"), "series_kind": transaction.get("series_kind")},
        )
        self.send_json({"transaction": transaction}, status=HTTPStatus.CREATED)

    def handle_update_transaction(self) -> None:
        user = self.require_user()
        transaction_id = self.path.split("?", 1)[0].split("/")[-1]
        data = self.read_json()
        previous = load_transaction_snapshot(user["id"], transaction_id)
        transaction = update_transaction(user["id"], transaction_id, data)
        metadata = {
            "amount": transaction.get("amount"),
            "type": transaction.get("type"),
            "date": transaction.get("date"),
            **change_metadata(previous, transaction, TRANSACTION_AUDIT_FIELDS),
        }
        self.record_operation(
            user["id"], "transactions", "update", "transaction",
            f"Lancamento atualizado: {transaction['description']}", transaction["id"],
            account_id=transaction.get("account_id"),
            operation_batch_id=transaction.get("series_id") if data.get("scope") == "future" else None,
            metadata=metadata,
        )
        self.send_json({"transaction": transaction})

    def handle_reconcile_transaction(self) -> None:
        user = self.require_user()
        transaction_id = self.path.split("?", 1)[0].split("/")[-2]
        data = self.read_json()
        transaction = set_transaction_reconciled(user["id"], transaction_id, bool(data.get("reconciled")))
        operation_type = "reconcile" if data.get("reconciled") else "unreconcile"
        self.record_operation(
            user["id"], "transactions", operation_type, "transaction",
            f"Lancamento {'conciliado' if data.get('reconciled') else 'desconciliado'}: {transaction['description']}",
            transaction["id"], account_id=transaction.get("account_id"),
        )
        self.send_json({"transaction": transaction})

    def handle_reconcile_credit_card_transaction(self) -> None:
        user = self.require_user()
        transaction_id = self.path.split("?", 1)[0].split("/")[-2]
        data = self.read_json()
        transaction = set_credit_card_transaction_reconciled(user["id"], transaction_id, bool(data.get("reconciled")))
        operation_type = "reconcile" if data.get("reconciled") else "unreconcile"
        self.record_operation(
            user["id"], "cards", operation_type, "credit_card_transaction",
            f"Lancamento de cartao {'conciliado' if data.get('reconciled') else 'desconciliado'}: {transaction['description']}",
            transaction["id"], credit_card_id=transaction.get("credit_card_id"),
            metadata={"invoice_month": transaction.get("invoice_month")},
        )
        self.send_json({"transaction": transaction})

    def handle_create_category(self) -> None:
        user = self.require_user()
        data = self.read_json()
        category = create_category(user["id"], data.get("name", ""), data.get("group_type", "expense"))
        self.record_operation(user["id"], "classifications", "create", "category", f"Categoria criada: {category['name']}", category["id"], metadata={"group_type": category.get("group_type")})
        self.send_json({"category": category}, status=HTTPStatus.CREATED)

    def handle_create_subcategory(self) -> None:
        user = self.require_user()
        data = self.read_json()
        subcategory = create_subcategory(user["id"], data.get("category_id", ""), data.get("name", ""))
        self.record_operation(user["id"], "classifications", "create", "subcategory", f"Subcategoria criada: {subcategory['name']}", subcategory["id"], metadata={"category_id": subcategory.get("category_id")})
        self.send_json({"subcategory": subcategory}, status=HTTPStatus.CREATED)

    def handle_create_tag(self) -> None:
        user = self.require_user()
        data = self.read_json()
        tag = create_tag(user["id"], data.get("name", ""))
        self.record_operation(user["id"], "classifications", "create", "tag", f"Tag criada: {tag['name']}", tag["id"])
        self.send_json({"tag": tag}, status=HTTPStatus.CREATED)

    def handle_create_spending_limit(self) -> None:
        user = self.require_user()
        data = self.read_json()
        spending_limit = create_spending_limit(user["id"], data)
        self.record_operation(
            user["id"], "limits", "create", "spending_limit",
            "Limite de gastos criado", spending_limit["id"],
            metadata={"month": spending_limit.get("month"), "category_id": spending_limit.get("category_id"), "subcategory_id": spending_limit.get("subcategory_id")},
        )
        self.send_json({"limit": spending_limit}, status=HTTPStatus.CREATED)

    def handle_update_account(self) -> None:
        user = self.require_user()
        account_id = self.path.rsplit("/", 1)[-1]
        data = self.read_json()
        account = update_checking_account(user["id"], account_id, data)
        self.record_operation(user["id"], "accounts", "update", "account", f"Conta atualizada: {account['name']}", account["id"], account_id=account["id"], metadata={"currency": account.get("currency")})
        self.send_json({"account": account})

    def handle_update_credit_card(self) -> None:
        user = self.require_user()
        card_id = self.path.rsplit("/", 1)[-1]
        data = self.read_json()
        card = update_credit_card(user["id"], card_id, data)
        self.record_operation(user["id"], "cards", "update", "credit_card", f"Cartao atualizado: {card['name']}", card["id"], credit_card_id=card["id"], metadata={"currency": card.get("currency")})
        self.send_json({"card": card})

    def handle_update_category(self) -> None:
        user = self.require_user()
        category_id = self.path.rsplit("/", 1)[-1]
        data = self.read_json()
        category = update_category(user["id"], category_id, data.get("name", ""))
        self.record_operation(user["id"], "classifications", "update", "category", f"Categoria atualizada: {category['name']}", category["id"], metadata={"group_type": category.get("group_type")})
        self.send_json({"category": category})

    def handle_update_subcategory(self) -> None:
        user = self.require_user()
        subcategory_id = self.path.rsplit("/", 1)[-1]
        data = self.read_json()
        subcategory = update_subcategory(user["id"], subcategory_id, data.get("name", ""))
        self.record_operation(user["id"], "classifications", "update", "subcategory", f"Subcategoria atualizada: {subcategory['name']}", subcategory["id"])
        self.send_json({"subcategory": subcategory})

    def handle_update_tag(self) -> None:
        user = self.require_user()
        tag_id = self.path.rsplit("/", 1)[-1]
        data = self.read_json()
        tag = update_tag(user["id"], tag_id, data.get("name", ""))
        self.record_operation(user["id"], "classifications", "update", "tag", f"Tag atualizada: {tag['name']}", tag["id"])
        self.send_json({"tag": tag})

    def handle_update_spending_limit(self) -> None:
        user = self.require_user()
        limit_id = self.path.rsplit("/", 1)[-1]
        data = self.read_json()
        spending_limit = update_spending_limit(user["id"], limit_id, data)
        self.record_operation(
            user["id"], "limits", "update", "spending_limit",
            "Limite de gastos atualizado", spending_limit["id"],
            metadata={"month": spending_limit.get("month"), "category_id": spending_limit.get("category_id"), "subcategory_id": spending_limit.get("subcategory_id")},
        )
        self.send_json({"limit": spending_limit})

    def handle_archive_account(self) -> None:
        user = self.require_user()
        account_id = self.path.rsplit("/", 1)[-1]
        archive_checking_account(user["id"], account_id)
        self.record_operation(user["id"], "accounts", "archive", "account", "Conta arquivada", account_id, account_id=account_id)
        self.send_json({"ok": True})

    def handle_archive_credit_card(self) -> None:
        user = self.require_user()
        card_id = self.path.rsplit("/", 1)[-1]
        archive_credit_card(user["id"], card_id)
        self.record_operation(user["id"], "cards", "archive", "credit_card", "Cartao arquivado", card_id, credit_card_id=card_id)
        self.send_json({"ok": True})

    def handle_restore_account(self) -> None:
        user = self.require_user()
        account_id = self.path.split("?", 1)[0].split("/")[-2]
        account = restore_checking_account(user["id"], account_id)
        self.record_operation(user["id"], "accounts", "restore", "account", f"Conta restaurada: {account['name']}", account["id"], account_id=account["id"])
        self.send_json({"account": account})

    def handle_restore_credit_card(self) -> None:
        user = self.require_user()
        card_id = self.path.split("?", 1)[0].split("/")[-2]
        card = restore_credit_card(user["id"], card_id)
        self.record_operation(user["id"], "cards", "restore", "credit_card", f"Cartao restaurado: {card['name']}", card["id"], credit_card_id=card["id"])
        self.send_json({"card": card})

    def handle_delete_transaction(self) -> None:
        user = self.require_user()
        transaction_id = self.route_path().rsplit("/", 1)[-1]
        delete_transaction(user["id"], transaction_id, apply_to_future=self.delete_scope_is_future())
        self.record_operation(user["id"], "transactions", "delete", "transaction", "Lancamento excluido", transaction_id)
        self.send_json({"ok": True})

    def handle_delete_credit_card_transaction(self) -> None:
        user = self.require_user()
        transaction_id = self.route_path().rsplit("/", 1)[-1]
        delete_credit_card_transaction(user["id"], transaction_id, apply_to_future=self.delete_scope_is_future())
        self.record_operation(user["id"], "cards", "delete", "credit_card_transaction", "Lancamento de cartao excluido", transaction_id)
        self.send_json({"ok": True})

    def delete_scope_is_future(self) -> bool:
        query = parse_qs(urlsplit(self.path).query)
        return (query.get("scope") or [""])[0] == "future"

    def handle_delete_category(self) -> None:
        user = self.require_user()
        category_id = self.path.rsplit("/", 1)[-1]
        delete_category(user["id"], category_id)
        self.record_operation(user["id"], "classifications", "delete", "category", "Categoria excluida", category_id)
        self.send_json({"ok": True})

    def handle_delete_subcategory(self) -> None:
        user = self.require_user()
        subcategory_id = self.path.rsplit("/", 1)[-1]
        delete_subcategory(user["id"], subcategory_id)
        self.record_operation(user["id"], "classifications", "delete", "subcategory", "Subcategoria excluida", subcategory_id)
        self.send_json({"ok": True})

    def handle_delete_tag(self) -> None:
        user = self.require_user()
        tag_id = self.path.rsplit("/", 1)[-1]
        delete_tag(user["id"], tag_id)
        self.record_operation(user["id"], "classifications", "delete", "tag", "Tag excluida", tag_id)
        self.send_json({"ok": True})

    def handle_delete_spending_limit(self) -> None:
        user = self.require_user()
        limit_id = self.path.rsplit("/", 1)[-1]
        delete_spending_limit(user["id"], limit_id)
        self.record_operation(user["id"], "limits", "delete", "spending_limit", "Limite de gastos excluido", limit_id)
        self.send_json({"ok": True})

    def handle_import_organizze_transactions(self) -> None:
        user = self.require_user()
        form = self.read_multipart()
        uploaded = form["files"].get("file")
        if not uploaded:
            raise ApiError("Envie o arquivo exportado pelo Organizze.")
        result = import_organizze_transactions(
            user["id"],
            form["fields"].get("account_id", ""),
            uploaded["content"],
            uploaded["filename"],
        )
        self.record_operation(
            user["id"], "imports", "import", "transaction",
            f"Importacao Organizze: {result.get('imported', 0)} lancamentos importados", None,
            account_id=form["fields"].get("account_id", ""),
            operation_batch_id=result.get("operation_batch_id"),
            metadata={"filename": uploaded["filename"], "imported": result.get("imported"), "skipped": result.get("skipped")},
        )
        self.send_json(result, status=HTTPStatus.CREATED)

    def handle_import_system_template(self) -> None:
        user = self.require_user()
        form = self.read_multipart()
        uploaded = form["files"].get("file")
        if not uploaded:
            raise ApiError("Envie o modelo preenchido.")
        result = import_system_template(
            user["id"],
            form["fields"].get("target", "account"),
            form["fields"].get("target_id") or form["fields"].get("account_id") or form["fields"].get("credit_card_id") or "",
            uploaded["content"],
            uploaded["filename"],
        )
        target = form["fields"].get("target", "account")
        target_id = form["fields"].get("target_id") or form["fields"].get("account_id") or form["fields"].get("credit_card_id") or ""
        self.record_operation(
            user["id"], "imports", "import", "transaction",
            f"Importacao de modelo: {result.get('imported', 0)} lancamentos importados", None,
            account_id=target_id if target == "account" else None,
            credit_card_id=target_id if target == "card" else None,
            operation_batch_id=result.get("operation_batch_id"),
            metadata={"filename": uploaded["filename"], "target": target, "imported": result.get("imported"), "skipped": result.get("skipped")},
        )
        self.send_json(result, status=HTTPStatus.CREATED)

    def handle_import_template_download(self) -> None:
        user = self.require_user()
        query = parse_qs(urlsplit(self.path).query)
        target = (query.get("target") or ["account"])[0]
        body = system_import_template(user["id"], target)
        filename = "modelo_importacao_cartao.xlsx" if target in {"card", "cartao"} else "modelo_importacao_conta.xlsx"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.send_security_headers()
        self.end_headers()
        self.wfile.write(body)

    def record_operation(
        self,
        user_id: int,
        module: str,
        operation_type: str,
        entity_type: str,
        description: str,
        entity_id: object | None = None,
        *,
        account_id: object | None = None,
        credit_card_id: object | None = None,
        operation_batch_id: object | None = None,
        metadata: dict | None = None,
    ) -> None:
        create_operation_log(
            user_id,
            module=module,
            operation_type=operation_type,
            entity_type=entity_type,
            entity_id=entity_id,
            account_id=account_id,
            credit_card_id=credit_card_id,
            operation_batch_id=operation_batch_id,
            description=description,
            metadata=metadata or {},
        )

    def serve_static(self) -> None:
        path = self.path.split("?", 1)[0]
        if path in ("", "/"):
            file_path = WEB_ROOT / "index.html"
        else:
            file_path = (WEB_ROOT / path.lstrip("/")).resolve()
            if not str(file_path).startswith(str(WEB_ROOT.resolve())):
                self.send_error(HTTPStatus.FORBIDDEN)
                return
        if not file_path.exists() or not file_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        body = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        if path.startswith("/assets/"):
            self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        else:
            self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.send_security_headers()
        self.end_headers()
        self.wfile.write(body)

    def require_user(self, allow_anonymous: bool = False) -> dict | None:
        token = self.get_cookie("session")
        user = get_current_user(token) if token else None
        if not user and not allow_anonymous:
            raise ApiError("Sessao expirada. Entre novamente.", HTTPStatus.UNAUTHORIZED)
        return user

    def read_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError as exc:
            raise ApiError("Content-Length invalido.", HTTPStatus.BAD_REQUEST) from exc
        if length < 0:
            raise ApiError("Content-Length invalido.", HTTPStatus.BAD_REQUEST)
        if length > MAX_JSON_BODY_BYTES:
            raise ApiError("JSON muito grande. Envie ate 1 MB.", HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        if length == 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ApiError("JSON invalido.", HTTPStatus.BAD_REQUEST) from exc

    def read_multipart(self) -> dict:
        content_type = self.headers.get("Content-Type", "")
        match = re.search(r"boundary=(?P<boundary>[^;]+)", content_type)
        if not match:
            raise ApiError("Formulario de upload invalido.")
        length = int(self.headers.get("Content-Length", 0))
        if length <= 0:
            raise ApiError("Envie o arquivo para importacao.")
        if length > 5 * 1024 * 1024:
            raise ApiError("Arquivo muito grande. Envie um arquivo de ate 5 MB.", HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        boundary = match.group("boundary").strip('"').encode("utf-8")
        body = self.rfile.read(length)
        fields = {}
        files = {}
        for part in body.split(b"--" + boundary):
            part = part.strip(b"\r\n")
            if not part or part == b"--" or b"\r\n\r\n" not in part:
                continue
            raw_headers, content = part.split(b"\r\n\r\n", 1)
            headers = raw_headers.decode("utf-8", "ignore")
            name_match = re.search(r'name="([^"]+)"', headers)
            if not name_match:
                continue
            name = name_match.group(1)
            filename_match = re.search(r'filename="([^"]*)"', headers)
            if filename_match:
                if content.endswith(b"\r\n"):
                    content = content[:-2]
                files[name] = {
                    "filename": Path(filename_match.group(1)).name,
                    "content": content,
                }
            else:
                fields[name] = content.decode("utf-8", "ignore").strip()
        return {"fields": fields, "files": files}

    def send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK, headers: dict | None = None) -> None:
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_security_headers()
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def send_security_headers(self) -> None:
        for key, value in SECURITY_HEADERS.items():
            self.send_header(key, value)

    def validate_mutation_source(self) -> bool:
        if not self.is_allowed_host(self.headers.get("Host", "")):
            self.send_json({"error": "Origem da requisicao nao permitida."}, HTTPStatus.FORBIDDEN)
            return False
        origin = self.headers.get("Origin")
        if not origin or not self.is_allowed_origin(origin):
            self.send_json({"error": "Origem da requisicao nao permitida."}, HTTPStatus.FORBIDDEN)
            return False
        return True

    def validate_read_source(self) -> bool:
        if not self.is_allowed_host(self.headers.get("Host", "")):
            self.send_json({"error": "Origem da requisicao nao permitida."}, HTTPStatus.FORBIDDEN)
            return False
        origin = self.headers.get("Origin")
        if origin and not self.is_allowed_origin(origin):
            self.send_json({"error": "Origem da requisicao nao permitida."}, HTTPStatus.FORBIDDEN)
            return False
        return True

    def is_allowed_host(self, host_header: str) -> bool:
        return normalize_netloc(host_header) in allowed_host_values()

    def is_allowed_origin(self, origin_header: str) -> bool:
        origin = urlsplit(origin_header)
        if not origin.scheme or not origin.netloc or origin.path not in {"", "/"}:
            return False
        return f"{origin.scheme.lower()}://{normalize_netloc(origin.netloc)}" in allowed_origin_values()

    def get_cookie(self, name: str) -> str | None:
        raw_cookie = self.headers.get("Cookie", "")
        for part in raw_cookie.split(";"):
            key, _, value = part.strip().partition("=")
            if key == name:
                return value
        return None

    def session_cookie(self, token: str) -> dict:
        return {"Set-Cookie": self.cookie_header(f"session={token}; Max-Age={SESSION_COOKIE_MAX_AGE_SECONDS}")}

    def expired_session_cookie(self) -> str:
        return self.cookie_header("session=; Max-Age=0")

    def cookie_header(self, value: str) -> str:
        attributes = [value, "Path=/", "SameSite=Lax", "HttpOnly"]
        if PUBLIC_URL.startswith("https://"):
            attributes.append("Secure")
        return "; ".join(attributes)

    def client_source_key(self) -> str:
        return str(self.client_address[0])

    def handle_one_request(self) -> None:
        try:
            super().handle_one_request()
        except Exception as exc:
            if is_database_busy_error(exc):
                message = "O banco esta ocupado por outra operacao. Aguarde alguns segundos e tente novamente."
                status = HTTPStatus.SERVICE_UNAVAILABLE
            else:
                message = getattr(exc, "message", "Erro inesperado.")
                status = getattr(exc, "status", HTTPStatus.INTERNAL_SERVER_ERROR)
            self.send_json({"error": message}, status)

    def log_message(self, format: str, *args: object) -> None:
        return


class ApiError(Exception):
    def __init__(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        self.message = message
        self.status = status
        super().__init__(message)


def is_database_busy_error(exc: Exception) -> bool:
    if not isinstance(exc, sqlite3.OperationalError):
        return False
    message = str(exc).lower()
    return "database is locked" in message or "database table is locked" in message or "database is busy" in message


TRANSACTION_AUDIT_FIELDS = (
    ("type", "Tipo"),
    ("description", "Descricao"),
    ("amount", "Valor"),
    ("date", "Data"),
    ("account_name", "Conta"),
    ("destination_account_name", "Conta destino"),
    ("category_name", "Categoria"),
    ("subcategory_name", "Subcategoria"),
    ("tag_name", "Tags"),
    ("notes", "Observacoes"),
)

CARD_TRANSACTION_AUDIT_FIELDS = (
    ("type", "Tipo"),
    ("description", "Descricao"),
    ("amount", "Valor"),
    ("date", "Data"),
    ("invoice_month", "Fatura"),
    ("category_name", "Categoria"),
    ("subcategory_name", "Subcategoria"),
    ("tag_name", "Tags"),
    ("notes", "Observacoes"),
)


def load_transaction_snapshot(user_id: int, transaction_id: object) -> dict | None:
    try:
        with get_connection() as conn:
            row = fetch_transaction(conn, user_id, int(transaction_id))
        return format_transaction(row) if row else None
    except Exception:
        return None


def load_card_transaction_snapshot(user_id: int, transaction_id: object) -> dict | None:
    try:
        with get_connection() as conn:
            row = fetch_card_transaction(conn, user_id, int(transaction_id))
        currency = row.get("card_currency", "BRL") if row else "BRL"
        return format_card_transaction(row, currency) if row else None
    except Exception:
        return None


def change_metadata(before: dict | None, after: dict, fields: tuple[tuple[str, str], ...]) -> dict:
    if not before:
        return {"changed_fields": [], "changes": []}
    changes = []
    for key, label in fields:
        previous = audit_value(before.get(key))
        current = audit_value(after.get(key))
        if previous != current:
            changes.append({"field": key, "label": label, "before": previous, "after": current})
    return {
        "changed_fields": [change["field"] for change in changes],
        "changes": changes,
    }


def audit_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)


def cockpit_payload(transactions: list[dict]) -> dict:
    totals = {"income": 0.0, "expense": 0.0, "investment": 0.0}
    category_rows = {"income": {}, "expense": {}, "investment": {}}
    planning = {
        "income": {},
        "expense": {},
        "investment": {},
    }
    for transaction in transactions:
        if is_credit_card_payment_transaction(transaction):
            continue
        report_type = cockpit_transaction_type(transaction)
        if not report_type:
            continue
        amount = float(transaction.get("amount_brl") or transaction.get("amount") or 0)
        totals[report_type] += amount
        label = cockpit_category_label(transaction)
        add_cockpit_group(category_rows[report_type], label, amount)
        if transaction.get("series_kind") == "recurring" or (report_type == "investment" and transaction.get("series_kind") != "single"):
            currency = cockpit_transaction_currency(transaction)
            original_amount = float(transaction.get("amount") or 0)
            add_cockpit_group(planning[report_type], label, original_amount, currency)
    savings_rate = totals["investment"] / totals["income"] if totals["income"] > 0 else 0
    return {
        "month_totals": {**totals, "savings_rate": savings_rate},
        "top_income": ranked_cockpit_rows(category_rows["income"], 3),
        "top_expenses": ranked_cockpit_rows(category_rows["expense"], 5),
        "planning": {
            "income": ranked_cockpit_rows(planning["income"]),
            "investment": ranked_cockpit_rows(planning["investment"]),
            "expense": ranked_cockpit_rows(planning["expense"]),
        },
    }


def is_credit_card_payment_transaction(transaction: dict) -> bool:
    # spec: relatorios/relatorios v2.1 — critério 6
    # (pagamento de fatura fica fora das analises mensais; a despesa detalhada
    #  ja esta nos lancamentos do cartao pela competencia da fatura)
    return bool(transaction.get("is_credit_card_payment"))


def cockpit_transaction_type(transaction: dict) -> str:
    if transaction.get("type") == "income":
        return "income"
    if transaction.get("type") == "expense":
        return "expense"
    if transaction.get("type") == "investment" or transaction.get("investment_operation"):
        return "investment"
    return ""


def cockpit_category_label(transaction: dict) -> str:
    category = transaction.get("category_name") or "Sem categoria"
    subcategory = transaction.get("subcategory_name") or ""
    return f"{category} / {subcategory}" if subcategory else category


def cockpit_transaction_currency(transaction: dict) -> str:
    return str(
        transaction.get("account_currency")
        or transaction.get("card_currency")
        or "BRL"
    ).upper()


def add_cockpit_group(groups: dict, label: str, amount: float, currency: str | None = None) -> None:
    key = (currency, label) if currency else label
    row = groups.setdefault(key, {"label": label, "total": 0.0, "count": 0})
    if currency:
        row["currency"] = currency
    row["total"] += amount
    row["count"] += 1


def ranked_cockpit_rows(groups: dict, limit: int | None = None) -> list[dict]:
    rows = sorted(
        groups.values(),
        key=lambda row: (row.get("currency", ""), -row["total"], row["label"]),
    )
    if limit and len(rows) > limit:
        visible = rows[:limit]
        other_total = sum(row["total"] for row in rows[limit:])
        other_count = sum(row["count"] for row in rows[limit:])
        if other_total > 0:
            visible.append({"label": "Outros", "total": other_total, "count": other_count})
        return visible
    return rows


def main() -> None:
    initialize_database()
    server = ThreadingHTTPServer((HOST, PORT), AppHandler)
    print(f"Sistema Financeiro rodando em {PUBLIC_URL}")
    warning = insecure_lan_warning(HOST, PUBLIC_URL)
    if warning:
        print(warning)
    server.serve_forever()


def insecure_lan_warning(host: str, public_url: str) -> str | None:
    if urlsplit(public_url).scheme.lower() != "http":
        return None
    normalized_host = host.strip().strip("[]").lower()
    if normalized_host in {"localhost", "127.0.0.1", "::1"}:
        return None
    try:
        if ipaddress.ip_address(normalized_host).is_loopback:
            return None
    except ValueError:
        pass
    return "AVISO DE SEGURANCA: app exposto na rede local via HTTP. Configure HTTPS para proteger credenciais e sessoes."


if __name__ == "__main__":
    main()
