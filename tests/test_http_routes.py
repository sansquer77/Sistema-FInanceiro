from __future__ import annotations

import unittest

from financeiro.http_routes import dispatch_route, resolve_route


class _Target:
    called = ""

    def handle_update_transaction(self) -> None:
        self.called = "transaction"


class HttpRoutesTest(unittest.TestCase):
    def test_exact_route_is_resolved(self) -> None:
        self.assertEqual(resolve_route("GET", "/api/portfolio"), "handle_portfolio")
        self.assertEqual(resolve_route("GET", "/api/portfolio/events"), "handle_portfolio_events")
        self.assertEqual(resolve_route("GET", "/api/reports/overview"), "handle_report_overview")
        self.assertEqual(resolve_route("GET", "/api/global-search"), "handle_global_search")
        self.assertEqual(resolve_route("GET", "/api/cockpit/notifications"), "handle_cockpit_notifications")
        self.assertEqual(resolve_route("GET", "/api/backup/settings"), "handle_backup_settings")
        self.assertEqual(resolve_route("PUT", "/api/backup/settings"), "handle_save_backup_settings")
        self.assertEqual(resolve_route("POST", "/api/backup/run"), "handle_run_backup")
        self.assertEqual(resolve_route("POST", "/api/backup/validate"), "handle_validate_backup_restore")
        self.assertEqual(resolve_route("POST", "/api/backup/restore"), "handle_restore_backup")
        self.assertEqual(
            resolve_route("POST", "/api/cockpit/notifications/mark-seen"),
            "handle_mark_cockpit_notifications_seen",
        )

    def test_more_specific_pattern_wins(self) -> None:
        self.assertEqual(resolve_route("PUT", "/api/transactions/42/reconciliation"), "handle_reconcile_transaction")

    def test_dispatch_invokes_handler_and_reports_match(self) -> None:
        target = _Target()
        self.assertTrue(dispatch_route(target, "PUT", "/api/transactions/42"))
        self.assertEqual(target.called, "transaction")

    def test_unknown_route_is_not_dispatched(self) -> None:
        self.assertIsNone(resolve_route("GET", "/api/unknown"))


if __name__ == "__main__":
    unittest.main()
