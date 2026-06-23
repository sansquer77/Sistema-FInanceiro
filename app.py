from __future__ import annotations

import json
import mimetypes
import os
import re
from datetime import date
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from urllib.parse import parse_qs

from financeiro.accounts import (
    archive_checking_account,
    create_checking_account,
    list_archived_checking_accounts,
    list_checking_accounts,
    restore_checking_account,
    update_checking_account,
)
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
)
from financeiro.credit_cards import (
    archive_credit_card,
    create_credit_card,
    create_credit_card_transaction,
    delete_credit_card_transaction,
    list_archived_credit_cards,
    list_credit_card_invoice,
    list_credit_card_payments,
    list_credit_card_transactions,
    list_credit_cards,
    pay_credit_card_invoice,
    restore_credit_card,
    set_credit_card_transaction_reconciled,
    update_credit_card_transaction,
    update_credit_card,
)
from financeiro.database import initialize_database
from financeiro.imports import import_organizze_transactions, import_system_template, system_import_template
from financeiro.portfolio import close_position, create_opening_position, delete_opening_position, get_portfolio, redeem_position, update_opening_position, update_position_value_override
from financeiro.spending_limits import (
    create_spending_limit,
    delete_spending_limit,
    list_spending_limits,
    update_spending_limit,
)
from financeiro.transactions import (
    create_transaction,
    delete_transaction,
    get_exchange_rate_to_brl,
    list_transactions,
    set_transaction_reconciled,
    update_transaction,
)

ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"
HOST = os.environ.get("APP_HOST", "127.0.0.1")
PORT = int(os.environ.get("APP_PORT", "8010"))
PUBLIC_URL = os.environ.get("APP_URL", f"http://sistema-financeiro.localhost:{PORT}")


class AppHandler(BaseHTTPRequestHandler):
    server_version = "SistemaFinanceiro/0.1"

    def do_GET(self) -> None:
        path = self.route_path()
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
        if path == "/api/cockpit":
            self.handle_cockpit()
            return
        if path == "/api/portfolio":
            self.handle_portfolio()
            return
        self.serve_static()

    def do_POST(self) -> None:
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
        self.send_json({"error": "Rota nao encontrada."}, HTTPStatus.NOT_FOUND)

    def do_PUT(self) -> None:
        path = self.route_path()
        if path.startswith("/api/transactions/") and path.endswith("/reconciliation"):
            self.handle_reconcile_transaction()
            return
        if path.startswith("/api/credit-card-transactions/") and path.endswith("/reconciliation"):
            self.handle_reconcile_credit_card_transaction()
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
        self.send_json({"error": "Rota nao encontrada."}, HTTPStatus.NOT_FOUND)

    def do_DELETE(self) -> None:
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
        user = login_user(data.get("email", ""), data.get("password", ""))
        token = create_session(user["id"])
        self.send_json({"user": user}, headers=self.session_cookie(token))

    def handle_logout(self) -> None:
        token = self.get_cookie("session")
        if token:
            logout_session(token)
        self.send_json({"ok": True}, headers={"Set-Cookie": "session=; Path=/; Max-Age=0; SameSite=Lax; HttpOnly"})

    def handle_password_reset_request(self) -> None:
        data = self.read_json()
        result = request_password_reset(data.get("email", ""))
        self.send_json(result)

    def handle_password_reset_confirm(self) -> None:
        data = self.read_json()
        reset_password(data.get("token", ""), data.get("new_password", ""))
        self.send_json({"ok": True})

    def handle_update_email(self) -> None:
        user = self.require_user()
        data = self.read_json()
        updated = update_user_email(user["id"], data.get("email", ""), data.get("current_password", ""))
        self.send_json({"user": updated})

    def handle_update_password(self) -> None:
        user = self.require_user()
        data = self.read_json()
        update_user_password(user["id"], data.get("current_password", ""), data.get("new_password", ""))
        self.send_json({"ok": True})

    def handle_delete_user(self) -> None:
        user = self.require_user()
        data = self.read_json()
        delete_user_account(user["id"], data.get("current_password", ""))
        self.send_json({"ok": True}, headers={"Set-Cookie": "session=; Path=/; Max-Age=0; SameSite=Lax; HttpOnly"})

    def handle_clear_launches(self) -> None:
        user = self.require_user()
        data = self.read_json()
        clear_user_launches(user["id"], data.get("current_password", ""))
        self.send_json({"ok": True})

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
        self.send_json(cockpit_payload(transactions))

    def handle_exchange_rate(self) -> None:
        self.require_user()
        query = parse_qs(urlsplit(self.path).query)
        currency = (query.get("currency") or ["BRL"])[0]
        transaction_date = (query.get("date") or [None])[0]
        rate = get_exchange_rate_to_brl(currency, transaction_date)
        self.send_json({"currency": currency.upper(), "date": transaction_date, "rate": f"{rate:.6f}"})

    def handle_list_categories(self) -> None:
        user = self.require_user()
        query = parse_qs(urlsplit(self.path).query)
        group_type = (query.get("group") or [None])[0]
        self.send_json({"categories": list_categories(user["id"], group_type)})

    def handle_list_tags(self) -> None:
        user = self.require_user()
        self.send_json({"tags": list_tags(user["id"])})

    def handle_list_spending_limits(self) -> None:
        user = self.require_user()
        query = parse_qs(urlsplit(self.path).query)
        month = (query.get("month") or [None])[0]
        self.send_json({"limits": list_spending_limits(user["id"], month)})

    def handle_portfolio(self) -> None:
        user = self.require_user()
        query = parse_qs(urlsplit(self.path).query)
        force_refresh = (query.get("refresh") or [""])[0].lower() in {"1", "true", "yes", "sim"}
        self.send_json(get_portfolio(user["id"], force_refresh=force_refresh))

    def handle_create_portfolio_position(self) -> None:
        user = self.require_user()
        data = self.read_json()
        self.send_json(create_opening_position(user["id"], data), status=HTTPStatus.CREATED)

    def handle_update_portfolio_position(self) -> None:
        user = self.require_user()
        position_id = self.route_path().rsplit("/", 1)[-1]
        data = self.read_json()
        self.send_json(update_opening_position(user["id"], position_id, data))

    def handle_delete_portfolio_position(self) -> None:
        user = self.require_user()
        position_id = self.route_path().rsplit("/", 1)[-1]
        self.send_json(delete_opening_position(user["id"], position_id))

    def handle_redeem_portfolio_position(self) -> None:
        user = self.require_user()
        data = self.read_json()
        self.send_json(redeem_position(user["id"], data), status=HTTPStatus.CREATED)

    def handle_close_portfolio_position(self) -> None:
        user = self.require_user()
        data = self.read_json()
        self.send_json(close_position(user["id"], data), status=HTTPStatus.CREATED)

    def handle_update_portfolio_value(self) -> None:
        user = self.require_user()
        data = self.read_json()
        self.send_json(update_position_value_override(user["id"], data))

    def handle_create_account(self) -> None:
        user = self.require_user()
        data = self.read_json()
        account = create_checking_account(user["id"], data)
        self.send_json({"account": account}, status=HTTPStatus.CREATED)

    def handle_create_credit_card(self) -> None:
        user = self.require_user()
        data = self.read_json()
        card = create_credit_card(user["id"], data)
        self.send_json({"card": card}, status=HTTPStatus.CREATED)

    def handle_create_credit_card_transaction(self) -> None:
        user = self.require_user()
        data = self.read_json()
        transaction = create_credit_card_transaction(user["id"], data)
        self.send_json({"transaction": transaction}, status=HTTPStatus.CREATED)

    def handle_update_credit_card_transaction(self) -> None:
        user = self.require_user()
        transaction_id = self.path.split("?", 1)[0].split("/")[-1]
        data = self.read_json()
        transaction = update_credit_card_transaction(user["id"], transaction_id, data)
        self.send_json({"transaction": transaction})

    def handle_pay_credit_card_invoice(self) -> None:
        user = self.require_user()
        data = self.read_json()
        result = pay_credit_card_invoice(user["id"], data)
        self.send_json(result, status=HTTPStatus.CREATED)

    def handle_create_transaction(self) -> None:
        user = self.require_user()
        data = self.read_json()
        transaction = create_transaction(user["id"], data)
        self.send_json({"transaction": transaction}, status=HTTPStatus.CREATED)

    def handle_update_transaction(self) -> None:
        user = self.require_user()
        transaction_id = self.path.split("?", 1)[0].split("/")[-1]
        data = self.read_json()
        transaction = update_transaction(user["id"], transaction_id, data)
        self.send_json({"transaction": transaction})

    def handle_reconcile_transaction(self) -> None:
        user = self.require_user()
        transaction_id = self.path.split("?", 1)[0].split("/")[-2]
        data = self.read_json()
        transaction = set_transaction_reconciled(user["id"], transaction_id, bool(data.get("reconciled")))
        self.send_json({"transaction": transaction})

    def handle_reconcile_credit_card_transaction(self) -> None:
        user = self.require_user()
        transaction_id = self.path.split("?", 1)[0].split("/")[-2]
        data = self.read_json()
        transaction = set_credit_card_transaction_reconciled(user["id"], transaction_id, bool(data.get("reconciled")))
        self.send_json({"transaction": transaction})

    def handle_create_category(self) -> None:
        user = self.require_user()
        data = self.read_json()
        category = create_category(user["id"], data.get("name", ""), data.get("group_type", "expense"))
        self.send_json({"category": category}, status=HTTPStatus.CREATED)

    def handle_create_subcategory(self) -> None:
        user = self.require_user()
        data = self.read_json()
        subcategory = create_subcategory(user["id"], data.get("category_id", ""), data.get("name", ""))
        self.send_json({"subcategory": subcategory}, status=HTTPStatus.CREATED)

    def handle_create_tag(self) -> None:
        user = self.require_user()
        data = self.read_json()
        tag = create_tag(user["id"], data.get("name", ""))
        self.send_json({"tag": tag}, status=HTTPStatus.CREATED)

    def handle_create_spending_limit(self) -> None:
        user = self.require_user()
        data = self.read_json()
        spending_limit = create_spending_limit(user["id"], data)
        self.send_json({"limit": spending_limit}, status=HTTPStatus.CREATED)

    def handle_update_account(self) -> None:
        user = self.require_user()
        account_id = self.path.rsplit("/", 1)[-1]
        data = self.read_json()
        account = update_checking_account(user["id"], account_id, data)
        self.send_json({"account": account})

    def handle_update_credit_card(self) -> None:
        user = self.require_user()
        card_id = self.path.rsplit("/", 1)[-1]
        data = self.read_json()
        card = update_credit_card(user["id"], card_id, data)
        self.send_json({"card": card})

    def handle_update_category(self) -> None:
        user = self.require_user()
        category_id = self.path.rsplit("/", 1)[-1]
        data = self.read_json()
        category = update_category(user["id"], category_id, data.get("name", ""))
        self.send_json({"category": category})

    def handle_update_subcategory(self) -> None:
        user = self.require_user()
        subcategory_id = self.path.rsplit("/", 1)[-1]
        data = self.read_json()
        subcategory = update_subcategory(user["id"], subcategory_id, data.get("name", ""))
        self.send_json({"subcategory": subcategory})

    def handle_update_tag(self) -> None:
        user = self.require_user()
        tag_id = self.path.rsplit("/", 1)[-1]
        data = self.read_json()
        tag = update_tag(user["id"], tag_id, data.get("name", ""))
        self.send_json({"tag": tag})

    def handle_update_spending_limit(self) -> None:
        user = self.require_user()
        limit_id = self.path.rsplit("/", 1)[-1]
        data = self.read_json()
        spending_limit = update_spending_limit(user["id"], limit_id, data)
        self.send_json({"limit": spending_limit})

    def handle_archive_account(self) -> None:
        user = self.require_user()
        account_id = self.path.rsplit("/", 1)[-1]
        archive_checking_account(user["id"], account_id)
        self.send_json({"ok": True})

    def handle_archive_credit_card(self) -> None:
        user = self.require_user()
        card_id = self.path.rsplit("/", 1)[-1]
        archive_credit_card(user["id"], card_id)
        self.send_json({"ok": True})

    def handle_restore_account(self) -> None:
        user = self.require_user()
        account_id = self.path.split("?", 1)[0].split("/")[-2]
        account = restore_checking_account(user["id"], account_id)
        self.send_json({"account": account})

    def handle_restore_credit_card(self) -> None:
        user = self.require_user()
        card_id = self.path.split("?", 1)[0].split("/")[-2]
        card = restore_credit_card(user["id"], card_id)
        self.send_json({"card": card})

    def handle_delete_transaction(self) -> None:
        user = self.require_user()
        transaction_id = self.route_path().rsplit("/", 1)[-1]
        delete_transaction(user["id"], transaction_id, apply_to_future=self.delete_scope_is_future())
        self.send_json({"ok": True})

    def handle_delete_credit_card_transaction(self) -> None:
        user = self.require_user()
        transaction_id = self.route_path().rsplit("/", 1)[-1]
        delete_credit_card_transaction(user["id"], transaction_id, apply_to_future=self.delete_scope_is_future())
        self.send_json({"ok": True})

    def delete_scope_is_future(self) -> bool:
        query = parse_qs(urlsplit(self.path).query)
        return (query.get("scope") or [""])[0] == "future"

    def handle_delete_category(self) -> None:
        user = self.require_user()
        category_id = self.path.rsplit("/", 1)[-1]
        delete_category(user["id"], category_id)
        self.send_json({"ok": True})

    def handle_delete_subcategory(self) -> None:
        user = self.require_user()
        subcategory_id = self.path.rsplit("/", 1)[-1]
        delete_subcategory(user["id"], subcategory_id)
        self.send_json({"ok": True})

    def handle_delete_tag(self) -> None:
        user = self.require_user()
        tag_id = self.path.rsplit("/", 1)[-1]
        delete_tag(user["id"], tag_id)
        self.send_json({"ok": True})

    def handle_delete_spending_limit(self) -> None:
        user = self.require_user()
        limit_id = self.path.rsplit("/", 1)[-1]
        delete_spending_limit(user["id"], limit_id)
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
        self.end_headers()
        self.wfile.write(body)

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
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def require_user(self, allow_anonymous: bool = False) -> dict | None:
        token = self.get_cookie("session")
        user = get_current_user(token) if token else None
        if not user and not allow_anonymous:
            raise ApiError("Sessao expirada. Entre novamente.", HTTPStatus.UNAUTHORIZED)
        return user

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
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
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def get_cookie(self, name: str) -> str | None:
        raw_cookie = self.headers.get("Cookie", "")
        for part in raw_cookie.split(";"):
            key, _, value = part.strip().partition("=")
            if key == name:
                return value
        return None

    def session_cookie(self, token: str) -> dict:
        return {"Set-Cookie": f"session={token}; Path=/; SameSite=Lax; HttpOnly"}

    def handle_one_request(self) -> None:
        try:
            super().handle_one_request()
        except Exception as exc:
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


def cockpit_payload(transactions: list[dict]) -> dict:
    totals = {"income": 0.0, "expense": 0.0, "investment": 0.0}
    category_rows = {"income": {}, "expense": {}, "investment": {}}
    planning = {
        "income": {},
        "expense": {},
        "investment": {},
    }
    for transaction in transactions:
        report_type = cockpit_transaction_type(transaction)
        if not report_type:
            continue
        amount = float(transaction.get("amount_brl") or transaction.get("amount") or 0)
        totals[report_type] += amount
        label = cockpit_category_label(transaction)
        add_cockpit_group(category_rows[report_type], label, amount)
        if transaction.get("series_kind") == "recurring" or (report_type == "investment" and transaction.get("series_kind") != "single"):
            add_cockpit_group(planning[report_type], label, amount)
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


def add_cockpit_group(groups: dict, label: str, amount: float) -> None:
    row = groups.setdefault(label, {"label": label, "total": 0.0, "count": 0})
    row["total"] += amount
    row["count"] += 1


def ranked_cockpit_rows(groups: dict, limit: int | None = None) -> list[dict]:
    rows = sorted(groups.values(), key=lambda row: (-row["total"], row["label"]))
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
    server.serve_forever()


if __name__ == "__main__":
    main()
