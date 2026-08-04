from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from financeiro import version_check as version_check_module
from financeiro.version_check import _parse_version, _version_greater, latest_version_info


class VersionParsingTest(unittest.TestCase):
    def test_parse_version_extracts_semver(self) -> None:
        self.assertEqual(_parse_version("v1.2.3"), (1, 2, 3))
        self.assertEqual(_parse_version("1.2.3"), (1, 2, 3))
        self.assertEqual(_parse_version("release-1.2.3"), (1, 2, 3))

    def test_parse_version_returns_none_for_invalid(self) -> None:
        self.assertIsNone(_parse_version(""))
        self.assertIsNone(_parse_version("latest"))
        self.assertIsNone(_parse_version("1.2"))

    def test_version_greater_comparison(self) -> None:
        self.assertTrue(_version_greater("1.3.0", "1.2.0"))
        self.assertTrue(_version_greater("2.0.0", "1.9.9"))
        self.assertTrue(_version_greater("1.2.1", "1.2.0"))
        self.assertFalse(_version_greater("1.2.0", "1.2.0"))
        self.assertFalse(_version_greater("1.1.0", "1.2.0"))
        self.assertFalse(_version_greater("1.2.0", None))


class LatestVersionInfoTest(unittest.TestCase):
    def setUp(self) -> None:
        self.original_cache = version_check_module._cache.copy()
        version_check_module._cache = {"fetched_at": None, "data": None}

    def tearDown(self) -> None:
        version_check_module._cache = self.original_cache

    @mock.patch("financeiro.version_check._fetch_latest_release")
    def test_returns_update_available_when_newer(self, mock_fetch) -> None:
        mock_fetch.return_value = {
            "version": "v1.3.0",
            "download_url": "https://example.com/download",
            "release_url": "https://example.com/release",
        }

        with mock.patch("financeiro.version_check.APP_VERSION", "1.2.0"):
            info = latest_version_info()

        self.assertEqual(info["current_version"], "1.2.0")
        self.assertEqual(info["latest_version"], "v1.3.0")
        self.assertTrue(info["update_available"])
        self.assertEqual(info["download_url"], "https://example.com/download")
        self.assertEqual(info["landing_url"], "https://sistemafinanceiropage.vercel.app/#downloads")

    @mock.patch("financeiro.version_check._fetch_latest_release")
    def test_returns_no_update_when_same_version(self, mock_fetch) -> None:
        mock_fetch.return_value = {
            "version": "v1.2.0",
            "download_url": "https://example.com/download",
            "release_url": "https://example.com/release",
        }

        with mock.patch("financeiro.version_check.APP_VERSION", "1.2.0"):
            info = latest_version_info()

        self.assertFalse(info["update_available"])

    @mock.patch("financeiro.version_check._fetch_latest_release")
    def test_returns_fallback_when_fetch_fails(self, mock_fetch) -> None:
        mock_fetch.return_value = None

        with mock.patch("financeiro.version_check.APP_VERSION", "1.2.0"):
            info = latest_version_info()

        self.assertEqual(info["current_version"], "1.2.0")
        self.assertIsNone(info["latest_version"])
        self.assertFalse(info["update_available"])
        self.assertEqual(info["download_url"], "https://github.com/sansquer77/Sistema-FInanceiro/releases")

    @mock.patch("financeiro.version_check._fetch_latest_release")
    def test_uses_cache_within_ttl(self, mock_fetch) -> None:
        mock_fetch.return_value = {"version": "v1.3.0"}

        with mock.patch("financeiro.version_check.APP_VERSION", "1.2.0"):
            latest_version_info()
            latest_version_info()

        self.assertEqual(mock_fetch.call_count, 1)

    @mock.patch("financeiro.version_check._fetch_latest_release")
    def test_refetches_after_ttl(self, mock_fetch) -> None:
        mock_fetch.return_value = {"version": "v1.3.0"}
        version_check_module._cache = {
            "fetched_at": datetime.now(timezone.utc) - timedelta(seconds=3700),
            "data": {"version": "v1.2.0"},
        }

        with mock.patch("financeiro.version_check.APP_VERSION", "1.2.0"):
            info = latest_version_info()

        self.assertEqual(mock_fetch.call_count, 1)
        self.assertEqual(info["latest_version"], "v1.3.0")


if __name__ == "__main__":
    unittest.main()
