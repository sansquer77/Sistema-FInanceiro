from __future__ import annotations

import os
import socket
import unittest
from unittest import mock
from urllib.error import HTTPError
from urllib.request import Request

from financeiro import ai_endpoint_security
from financeiro.ai_endpoint_security import (
    AIEndpointSecurityError,
    allow_private_endpoints,
    allowed_local_hosts,
    create_ai_opener,
    is_private_ip,
    validate_ai_base_url,
)


class AIEndpointSecurityTest(unittest.TestCase):
    def tearDown(self) -> None:
        os.environ.pop("AI_ALLOW_PRIVATE_ENDPOINTS", None)
        os.environ.pop("AI_ALLOWED_LOCAL_HOSTS", None)

    def _patch_resolve(self, ips: list[str]):
        """Mock de socket.getaddrinfo para retornar os IPs fornecidos."""
        def fake_getaddrinfo(host, port, *args, **kwargs):
            return [
                (socket.AF_INET if "." in ip else socket.AF_INET6, None, None, None, (ip, 0))
                for ip in ips
            ]
        return mock.patch("financeiro.ai_endpoint_security.socket.getaddrinfo", side_effect=fake_getaddrinfo)

    def test_https_public_url_is_accepted(self) -> None:
        with self._patch_resolve(["20.0.0.1"]):
            url = validate_ai_base_url("https://api.exemplo.com")
        self.assertEqual(url, "https://api.exemplo.com")

    def test_http_public_url_is_rejected(self) -> None:
        with self._patch_resolve(["20.0.0.1"]):
            with self.assertRaises(AIEndpointSecurityError):
                validate_ai_base_url("http://api.exemplo.com")

    def test_http_private_url_accepted_when_allowed(self) -> None:
        os.environ["AI_ALLOW_PRIVATE_ENDPOINTS"] = "true"
        url = validate_ai_base_url("http://127.0.0.1:11434")
        self.assertEqual(url, "http://127.0.0.1:11434")

    def test_http_localhost_accepted_when_allowed(self) -> None:
        os.environ["AI_ALLOW_PRIVATE_ENDPOINTS"] = "true"
        with self._patch_resolve(["127.0.0.1"]):
            url = validate_ai_base_url("http://localhost:11434")
        self.assertEqual(url, "http://localhost:11434")

    def test_private_ip_rejected_without_permission(self) -> None:
        with self.assertRaises(AIEndpointSecurityError):
            validate_ai_base_url("http://192.168.1.10:11434")

    def test_private_hostname_rejected_without_permission(self) -> None:
        with self._patch_resolve(["192.168.1.10"]):
            with self.assertRaises(AIEndpointSecurityError):
                validate_ai_base_url("https://ollama.local:11434")

    def test_invalid_scheme_is_rejected(self) -> None:
        with self.assertRaises(AIEndpointSecurityError):
            validate_ai_base_url("ftp://exemplo.com/v1")

    def test_credentials_in_url_are_rejected(self) -> None:
        with self.assertRaises(AIEndpointSecurityError):
            validate_ai_base_url("https://user:pass@exemplo.com")

    def test_invalid_port_is_rejected(self) -> None:
        with self.assertRaises(AIEndpointSecurityError):
            validate_ai_base_url("https://exemplo.com:99999")

    def test_query_string_is_rejected(self) -> None:
        with self.assertRaises(AIEndpointSecurityError):
            validate_ai_base_url("https://exemplo.com?x=1")

    def test_fragment_is_rejected(self) -> None:
        with self.assertRaises(AIEndpointSecurityError):
            validate_ai_base_url("https://exemplo.com#secao")

    def test_path_traversal_in_base_url_is_rejected(self) -> None:
        with self.assertRaises(AIEndpointSecurityError):
            validate_ai_base_url("https://exemplo.com/v1/../v2")

    def test_double_slash_in_base_url_is_rejected(self) -> None:
        with self.assertRaises(AIEndpointSecurityError):
            validate_ai_base_url("https://exemplo.com//v1")

    def test_explicitly_allowed_local_host_is_accepted(self) -> None:
        os.environ["AI_ALLOW_PRIVATE_ENDPOINTS"] = "true"
        os.environ["AI_ALLOWED_LOCAL_HOSTS"] = "ollama.local,lmstudio.local"
        url = validate_ai_base_url("http://ollama.local:11434")
        self.assertEqual(url, "http://ollama.local:11434")

    def test_allowed_local_host_requires_private_flag(self) -> None:
        os.environ["AI_ALLOWED_LOCAL_HOSTS"] = "ollama.local"
        with self.assertRaises(AIEndpointSecurityError):
            validate_ai_base_url("http://ollama.local:11434")

    def test_unresolvable_hostname_is_rejected(self) -> None:
        with mock.patch("financeiro.ai_endpoint_security.socket.getaddrinfo", side_effect=OSError("nxdomain")):
            with self.assertRaises(AIEndpointSecurityError):
                validate_ai_base_url("https://nao.existe.invalid")

    def test_private_ip_detection(self) -> None:
        self.assertTrue(is_private_ip("127.0.0.1"))
        self.assertTrue(is_private_ip("10.0.0.1"))
        self.assertTrue(is_private_ip("192.168.1.1"))
        self.assertTrue(is_private_ip("172.16.0.1"))
        self.assertTrue(is_private_ip("169.254.1.1"))
        self.assertTrue(is_private_ip("::1"))
        self.assertTrue(is_private_ip("fe80::1"))
        self.assertFalse(is_private_ip("8.8.8.8"))
        self.assertFalse(is_private_ip("2001:4860:4860::8888"))

    def test_opener_blocks_redirects(self) -> None:
        opener = create_ai_opener()
        request = Request("http://127.0.0.1:1234/test")
        redirect_response = mock.Mock()
        redirect_response.getcode.return_value = 302
        redirect_response.headers = {"Location": "http://127.0.0.1:1234/other"}
        with mock.patch.object(opener, "_open", return_value=redirect_response):
            response = opener.open(request, timeout=1)
        self.assertEqual(response.getcode(), 302)

    def test_env_helpers(self) -> None:
        self.assertFalse(allow_private_endpoints())
        self.assertEqual(allowed_local_hosts(), set())
        os.environ["AI_ALLOW_PRIVATE_ENDPOINTS"] = "true"
        os.environ["AI_ALLOWED_LOCAL_HOSTS"] = "A.local, B.local ,"
        self.assertTrue(allow_private_endpoints())
        self.assertEqual(allowed_local_hosts(), {"a.local", "b.local"})


class AIEndpointSecurityIntegrationTest(unittest.TestCase):
    """Garante que a validacao e o opener seguro sao usados nos callers de IA."""

    def tearDown(self) -> None:
        os.environ.pop("AI_ALLOW_PRIVATE_ENDPOINTS", None)

    def test_ai_summary_returns_none_on_ssrf_validation_failure(self) -> None:
        from financeiro.ai_summary import generate_ai_summary
        from financeiro.secure_config import save_ai_settings
        from financeiro import database
        from financeiro.auth import create_user
        import tempfile
        from pathlib import Path

        tempdir = tempfile.TemporaryDirectory()
        original_data_dir = database.DATA_DIR
        original_db_path = database.DB_PATH
        database.DATA_DIR = Path(tempdir.name)
        database.DB_PATH = database.DATA_DIR / "test-ai-ssrf.db"
        database.initialize_database()
        try:
            user = create_user("SSRF", "ssrf@example.com", "strong-password")
            os.environ["AI_ALLOW_PRIVATE_ENDPOINTS"] = "true"
            save_ai_settings(user["id"], {
                "provider": "local",
                "enabled": True,
                "base_url": "http://192.168.1.10:11434",
                "model": "model",
                "auth_type": "none",
            })
            os.environ.pop("AI_ALLOW_PRIVATE_ENDPOINTS", None)
            summary = generate_ai_summary(user["id"], {"month": "2026-07", "resumo_local": "Local"})
            self.assertIsNone(summary)
        finally:
            database.DATA_DIR = original_data_dir
            database.DB_PATH = original_db_path
            tempdir.cleanup()

    def test_consultor_provider_rejects_ssrf_url(self) -> None:
        from financeiro import consultor
        from financeiro.consultor_errors import ConsultorError

        messages = consultor.build_ai_messages("Prompt", {"x": 1})
        with self.assertRaises(ConsultorError):
            consultor.call_consultor_ai_provider(
                {
                    "provider": "custom",
                    "base_url": "http://192.168.1.10:11434",
                    "model": "model",
                    "api_key": "",
                    "auth_type": "none",
                },
                messages,
                max_tokens=100,
                timeout_seconds=5,
            )


if __name__ == "__main__":
    unittest.main()
