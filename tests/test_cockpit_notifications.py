from __future__ import annotations

import tempfile
import unittest
from unittest import mock
from datetime import date
from pathlib import Path

from financeiro import database
from financeiro.auth import create_user
from financeiro.cockpit_notifications import build_cockpit_notifications, mark_informational_seen
import app


class CockpitNotificationsTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.old_paths = database.DATA_DIR, database.DB_PATH
        database.DATA_DIR = Path(self.tempdir.name)
        database.DB_PATH = database.DATA_DIR / "notifications.db"
        database.initialize_database()
        self.user = create_user("Alice", "alice@example.com", "strong-password")
        self.today = date(2026, 9, 3)

    def tearDown(self):
        database.DATA_DIR, database.DB_PATH = self.old_paths
        self.tempdir.cleanup()

    def build(self, **kwargs):
        defaults = {
            "reference_date": self.today,
            "limits_loader": lambda _user, _month: [],
            "totals_loader": lambda _user, _month: [],
            "calendar_loader": lambda _user, **_kwargs: {"overdue_payables": [], "maturity_30_days": []},
        }
        defaults.update(kwargs)
        return build_cockpit_notifications(self.user["id"], **defaults)

    def test_compiles_limit_negative_balance_and_overdue_account(self):
        payload = self.build(
            limits_loader=lambda _user, _month: [{
                "id": 7, "category_name": "Alimentação", "subcategory_name": None,
                "spent_amount_cents": 135000, "limit_amount_cents": 120000,
            }],
            totals_loader=lambda _user, _month: [{"currency": "BRL", "current": "-10.50"}],
            calendar_loader=lambda _user, **_kwargs: {
                "overdue_payables": [{"id": 9, "date": "2026-09-01", "description": "Conta", "account_name": "Banco", "account_id": 3}],
                "maturity_30_days": [],
            },
        )
        self.assertEqual(payload["critical_count"], 3)
        self.assertEqual({item["type"] for item in payload["critical"]}, {
            "limit_exceeded", "projected_negative_balance", "overdue_payable",
        })

    def test_informational_seen_state_is_persistent_but_item_remains_visible(self):
        event = {"id": "ITUB4:2026-09-05", "asset_identifier": "ITUB4", "payment_date": "2026-09-05", "source": "Yahoo", "confirmation_level": "detectado"}
        first = self.build(portfolio_events=[event])
        self.assertEqual(first["informational_count"], 1)
        notification_id = first["informational"][0]["id"]
        self.assertEqual(mark_informational_seen(self.user["id"], [notification_id]), 1)
        second = self.build(portfolio_events=[event])
        self.assertEqual(second["informational_count"], 0)
        self.assertEqual(len(second["informational"]), 1)
        self.assertTrue(second["informational"][0]["seen"])

    def test_external_portfolio_failure_does_not_create_critical_alert(self):
        payload = self.build(portfolio_positions_loader=lambda _user: (_ for _ in ()).throw(RuntimeError("offline")))
        self.assertEqual(payload["critical"], [])
        self.assertEqual(payload["informational"], [])

    def test_events_outside_current_week_are_not_listed(self):
        payload = self.build(portfolio_events=[{
            "id": "old", "asset_identifier": "PETR4", "payment_date": "2026-09-12",
        }])
        self.assertEqual(payload["informational"], [])

    def test_overdue_unpaid_invoice_is_critical(self):
        with database.get_connection() as conn:
            card_id = conn.execute(
                """
                INSERT INTO credit_cards (
                    user_id, name, issuer, currency, limit_cents, closing_day, due_day
                ) VALUES (?, 'Cartão teste', 'Banco teste', 'BRL', 100000, 20, 5)
                """,
                (self.user["id"],),
            ).lastrowid
            conn.execute(
                """
                INSERT INTO credit_card_transactions (
                    user_id, credit_card_id, type, description, amount_cents,
                    amount_brl_cents, date, invoice_month
                ) VALUES (?, ?, 'expense', 'Compra', 2500, 2500, '2026-08-01', '2026-08')
                """,
                (self.user["id"], card_id),
            )
        payload = self.build()
        overdue = [item for item in payload["critical"] if item["type"] == "overdue_invoice"]
        self.assertEqual(len(overdue), 1)
        self.assertEqual(overdue[0]["action"]["params"], {"card_id": card_id, "month": "2026-08"})

    def test_seen_state_is_isolated_by_user(self):
        other = create_user("Bob", "bob@example.com", "strong-password")
        event = {"id": "shared", "asset_identifier": "ITUB4", "payment_date": "2026-09-05"}
        notification_id = self.build(portfolio_events=[event])["informational"][0]["id"]
        mark_informational_seen(self.user["id"], [notification_id])
        other_payload = build_cockpit_notifications(
            other["id"], reference_date=self.today, portfolio_events=[event],
            limits_loader=lambda _user, _month: [], totals_loader=lambda _user, _month: [],
            calendar_loader=lambda _user, **_kwargs: {"overdue_payables": [], "maturity_30_days": []},
        )
        self.assertFalse(other_payload["informational"][0]["seen"])
        self.assertEqual(other_payload["informational_count"], 1)

    def test_get_route_is_authenticated_and_returns_domain_payload(self):
        handler = object.__new__(app.AppHandler)
        handler.headers = {"Host": "sistema-financeiro.localhost:8020"}
        handler.send_json = mock.Mock()
        with (
            mock.patch.object(app.AppHandler, "validate_read_source", return_value=True),
            mock.patch.object(app.AppHandler, "require_user", return_value=self.user) as require_user,
            mock.patch("app.get_portfolio_events", return_value={"events": []}) as events,
            mock.patch("app.build_cockpit_notifications", return_value={"critical": [], "informational": []}),
            mock.patch("app.date") as current_date,
        ):
            current_date.today.return_value = self.today
            handler.handle_cockpit_notifications()
        require_user.assert_called_once_with()
        events.assert_called_once_with(self.user["id"], start_date=date(2026, 8, 31))
        handler.send_json.assert_called_once_with({"critical": [], "informational": []})

    def test_get_route_does_not_build_payload_when_authentication_fails(self):
        handler = object.__new__(app.AppHandler)
        with (
            mock.patch.object(app.AppHandler, "validate_read_source", return_value=True),
            mock.patch.object(app.AppHandler, "require_user", side_effect=app.ApiError("Não autenticado", 401)),
            mock.patch("app.get_portfolio_events") as events,
            mock.patch("app.build_cockpit_notifications") as build,
        ):
            with self.assertRaises(app.ApiError):
                handler.handle_cockpit_notifications()
        build.assert_not_called()
        events.assert_not_called()

    def test_mark_seen_route_validates_payload_and_isolates_user(self):
        handler = object.__new__(app.AppHandler)
        handler.send_json = mock.Mock()
        handler.read_json = mock.Mock(return_value={"notification_ids": ["event:1", "event:1"]})
        with mock.patch.object(app.AppHandler, "require_user", return_value=self.user):
            handler.handle_mark_cockpit_notifications_seen()
        handler.send_json.assert_called_once_with({"status": "ok", "marked_count": 1})
        with database.get_connection() as conn:
            row = conn.execute("SELECT user_id, notification_id FROM notification_reads").fetchone()
        self.assertEqual((row["user_id"], row["notification_id"]), (self.user["id"], "event:1"))

    def test_mark_seen_route_rejects_non_list_payload(self):
        handler = object.__new__(app.AppHandler)
        handler.read_json = mock.Mock(return_value={"notification_ids": "event:1"})
        with mock.patch.object(app.AppHandler, "require_user", return_value=self.user):
            with self.assertRaises(app.ApiError):
                handler.handle_mark_cockpit_notifications_seen()

    def test_mark_seen_rejects_oversized_identifier(self):
        with self.assertRaises(ValueError):
            mark_informational_seen(self.user["id"], ["x" * 201])


if __name__ == "__main__":
    unittest.main()
