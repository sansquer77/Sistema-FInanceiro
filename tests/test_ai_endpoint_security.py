from __future__ import annotations

import os
import socket
import ssl
import unittest
from unittest import mock
from urllib.error import HTTPError
from urllib.request import Request

from financeiro import ai_endpoint_security
from financeiro.ai_endpoint_security import (
    AIEndpointSecurityError,
    allow_private_endpoints,
    allowed_local_endpoints,
    allowed_local_hosts,
    create_ai_opener,
    is_private_ip,
    validate_ai_base_url,
)


class AIEndpointSecurityTest(unittest.TestCase):
    def tearDown(self) -> None:
        os.environ.pop("AI_ALLOW_PRIVATE_ENDPOINTS", None)
        os.environ.pop("AI_ALLOWED_LOCAL_HOSTS", None)
        os.environ.pop("AI_ALLOWED_LOCAL_ENDPOINTS", None)

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
        os.environ["AI_ALLOWED_LOCAL_ENDPOINTS"] = "127.0.0.1:11434"
        url = validate_ai_base_url("http://127.0.0.1:11434")
        self.assertEqual(url, "http://127.0.0.1:11434")

    def test_http_localhost_accepted_when_allowed(self) -> None:
        os.environ["AI_ALLOW_PRIVATE_ENDPOINTS"] = "true"
        os.environ["AI_ALLOWED_LOCAL_ENDPOINTS"] = "localhost:11434"
        with self._patch_resolve(["127.0.0.1"]):
            url = validate_ai_base_url("http://localhost:11434")
        self.assertEqual(url, "http://localhost:11434")

    def test_private_ip_rejected_without_permission(self) -> None:
        with self.assertRaises(AIEndpointSecurityError):
            validate_ai_base_url("http://192.168.1.10:11434")

    def test_private_ip_rejected_without_allowlist(self) -> None:
        os.environ["AI_ALLOW_PRIVATE_ENDPOINTS"] = "true"
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

    def test_allowed_local_endpoint_requires_port_match(self) -> None:
        os.environ["AI_ALLOW_PRIVATE_ENDPOINTS"] = "true"
        os.environ["AI_ALLOWED_LOCAL_ENDPOINTS"] = "ollama.local:11434"
        with self._patch_resolve(["192.168.1.10"]):
            url = validate_ai_base_url("http://ollama.local:11434")
        self.assertEqual(url, "http://ollama.local:11434")
        with self.assertRaises(AIEndpointSecurityError):
            validate_ai_base_url("http://ollama.local:11435")

    def test_allowed_local_endpoint_accepts_resolved_ip(self) -> None:
        os.environ["AI_ALLOW_PRIVATE_ENDPOINTS"] = "true"
        os.environ["AI_ALLOWED_LOCAL_ENDPOINTS"] = "192.168.1.10:11434"
        with self._patch_resolve(["192.168.1.10"]):
            url = validate_ai_base_url("http://ollama.local:11434")
        self.assertEqual(url, "http://ollama.local:11434")

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

    def test_env_helpers(self) -> None:
        self.assertFalse(allow_private_endpoints())
        self.assertEqual(allowed_local_hosts(), set())
        self.assertEqual(allowed_local_endpoints(), set())
        os.environ["AI_ALLOW_PRIVATE_ENDPOINTS"] = "true"
        os.environ["AI_ALLOWED_LOCAL_HOSTS"] = "A.local, B.local ,"
        os.environ["AI_ALLOWED_LOCAL_ENDPOINTS"] = "X.local:1234, Y.local:5678 ,"
        self.assertTrue(allow_private_endpoints())
        self.assertEqual(allowed_local_hosts(), {"a.local", "b.local"})
        self.assertEqual(
            allowed_local_endpoints(),
            {("x.local", 1234), ("y.local", 5678)},
        )


class _FakeSocket:
    """Socket falso que registra o que foi enviado e devolve uma resposta HTTP valida."""

    def __init__(self) -> None:
        self.sent = b""

    def sendall(self, data: bytes) -> None:
        self.sent += data

    def makefile(self, mode: str, buffering: int | None = None):
        import io
        return io.BytesIO(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\n{}")

    def close(self) -> None:
        pass


class AIEndpointSecurityTransportTest(unittest.TestCase):
    """Testa o transporte de IA com DNS pinning, Host/SNI preservados e redirecionamentos bloqueados."""

    def tearDown(self) -> None:
        os.environ.pop("AI_ALLOW_PRIVATE_ENDPOINTS", None)
        os.environ.pop("AI_ALLOWED_LOCAL_HOSTS", None)
        os.environ.pop("AI_ALLOWED_LOCAL_ENDPOINTS", None)

    def _patch_resolution(self, ips: list[str]):
        """Mock de getaddrinfo retornando uma lista de IPs."""
        def fake_getaddrinfo(host, port, *args, **kwargs):
            return [
                (socket.AF_INET if "." in ip else socket.AF_INET6, None, None, None, (ip, 0))
                for ip in ips
            ]
        return mock.patch("financeiro.ai_endpoint_security.socket.getaddrinfo", side_effect=fake_getaddrinfo)

    def test_transport_pins_to_validated_ip(self) -> None:
        request = Request(
            "https://api.example.com/v1/chat/completions",
            data=b'{"x":1}',
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        fake_sock = _FakeSocket()
        context = ssl.create_default_context()

        with self._patch_resolution(["20.0.0.1"]), \
                mock.patch("financeiro.ai_endpoint_security.socket.create_connection", return_value=fake_sock) as create_conn, \
                mock.patch.object(context, "wrap_socket", return_value=fake_sock) as wrap:
            with ai_endpoint_security.ai_urlopen(request, timeout=5, context=context) as response:
                pass

        create_conn.assert_called_once_with(("20.0.0.1", 443), 5, None)
        wrap.assert_called_once()
        self.assertEqual(wrap.call_args.kwargs.get("server_hostname"), "api.example.com")
        self.assertIn(b"Host: api.example.com", fake_sock.sent)

    def test_transport_preserves_host_header_http(self) -> None:
        request = Request(
            "http://ollama.local:11434/api/generate",
            data=b'{"x":1}',
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        fake_sock = _FakeSocket()
        os.environ["AI_ALLOW_PRIVATE_ENDPOINTS"] = "true"
        os.environ["AI_ALLOWED_LOCAL_ENDPOINTS"] = "ollama.local:11434"

        with self._patch_resolution(["192.168.1.10"]), \
                mock.patch("financeiro.ai_endpoint_security.socket.create_connection", return_value=fake_sock) as create_conn:
            with ai_endpoint_security.ai_urlopen(request, timeout=5) as response:
                pass

        create_conn.assert_called_once_with(("192.168.1.10", 11434), 5, None)
        self.assertIn(b"Host: ollama.local:11434", fake_sock.sent)

    def test_transport_ipv4(self) -> None:
        request = Request("https://api.example.com/v1")
        fake_sock = _FakeSocket()
        with self._patch_resolution(["1.2.3.4"]), \
                mock.patch("financeiro.ai_endpoint_security.socket.create_connection", return_value=fake_sock) as create_conn, \
                mock.patch.object(ssl.SSLContext, "wrap_socket", return_value=fake_sock):
            with ai_endpoint_security.ai_urlopen(request, context=ssl.create_default_context()) as response:
                pass
        create_conn.assert_called_once_with(("1.2.3.4", 443), None, None)

    def test_transport_ipv6(self) -> None:
        request = Request("https://api.example.com/v1")
        fake_sock = _FakeSocket()

        def fake_getaddrinfo(host, port, *args, **kwargs):
            return [(socket.AF_INET6, None, None, None, ("2001:4860:4860::8888", 0, 0, 0))]

        with mock.patch("financeiro.ai_endpoint_security.socket.getaddrinfo", side_effect=fake_getaddrinfo), \
                mock.patch("financeiro.ai_endpoint_security.socket.create_connection", return_value=fake_sock) as create_conn, \
                mock.patch.object(ssl.SSLContext, "wrap_socket", return_value=fake_sock):
            with ai_endpoint_security.ai_urlopen(request, context=ssl.create_default_context()) as response:
                pass
        create_conn.assert_called_once_with(("2001:4860:4860::8888", 443), None, None)

    def test_transport_resolves_only_once(self) -> None:
        """DNS pinning: getaddrinfo e chamado uma unica vez durante ai_urlopen."""
        request = Request("https://api.example.com/v1")
        fake_sock = _FakeSocket()
        resolver = mock.Mock(side_effect=[
            [(socket.AF_INET, None, None, None, ("20.0.0.1", 0))],
        ])

        with mock.patch("financeiro.ai_endpoint_security.socket.getaddrinfo", side_effect=resolver), \
                mock.patch("financeiro.ai_endpoint_security.socket.create_connection", return_value=fake_sock), \
                mock.patch.object(ssl.SSLContext, "wrap_socket", return_value=fake_sock):
            with ai_endpoint_security.ai_urlopen(request, context=ssl.create_default_context()) as response:
                pass

        self.assertEqual(resolver.call_count, 1)

    def test_transport_rejects_private_without_allowlist(self) -> None:
        request = Request("http://192.168.1.10:11434/v1")
        with self.assertRaises(AIEndpointSecurityError):
            with ai_endpoint_security.ai_urlopen(request, timeout=5) as response:
                pass

    def test_transport_allowlist_by_host_and_port(self) -> None:
        request = Request("http://ollama.local:11434/api/generate")
        fake_sock = _FakeSocket()
        os.environ["AI_ALLOW_PRIVATE_ENDPOINTS"] = "true"
        os.environ["AI_ALLOWED_LOCAL_ENDPOINTS"] = "ollama.local:11434"

        with self._patch_resolution(["192.168.1.10"]), \
                mock.patch("financeiro.ai_endpoint_security.socket.create_connection", return_value=fake_sock):
            with ai_endpoint_security.ai_urlopen(request, timeout=5) as response:
                pass

    def test_transport_redirect_is_not_followed(self) -> None:
        request = Request("https://api.example.com/v1/chat/completions", data=b"{}", method="POST")
        response_mock = mock.Mock()
        response_mock.status = 302
        response_mock.headers = {"Location": "https://attacker.com/evil"}
        response_mock.read.return_value = b""
        response_mock.getcode.return_value = 302

        fake_sock = _FakeSocket()
        conn_class = "financeiro.ai_endpoint_security._PinnedHTTPSConnection"

        with self._patch_resolution(["20.0.0.1"]), \
                mock.patch("financeiro.ai_endpoint_security.socket.create_connection", return_value=fake_sock), \
                mock.patch.object(ssl.SSLContext, "wrap_socket", return_value=fake_sock), \
                mock.patch(f"{conn_class}.getresponse", return_value=response_mock):
            with ai_endpoint_security.ai_urlopen(request, context=ssl.create_default_context()) as response:
                self.assertEqual(response.status, 302)

    def test_transport_redirect_to_private_is_not_followed(self) -> None:
        request = Request("http://ollama.local:11434/api/generate", data=b"{}", method="POST")
        response_mock = mock.Mock()
        response_mock.status = 302
        response_mock.headers = {"Location": "http://192.168.1.20/internal"}
        response_mock.read.return_value = b""

        fake_sock = _FakeSocket()
        os.environ["AI_ALLOW_PRIVATE_ENDPOINTS"] = "true"
        os.environ["AI_ALLOWED_LOCAL_ENDPOINTS"] = "ollama.local:11434"

        with self._patch_resolution(["192.168.1.10"]), \
                mock.patch("financeiro.ai_endpoint_security.socket.create_connection", return_value=fake_sock), \
                mock.patch("financeiro.ai_endpoint_security._PinnedHTTPConnection.getresponse", return_value=response_mock):
            with ai_endpoint_security.ai_urlopen(request, timeout=5) as response:
                self.assertEqual(response.status, 302)


class AIEndpointSecurityIntegrationTest(unittest.TestCase):
    """Garante que a validacao e o opener seguro sao usados nos callers de IA."""

    def tearDown(self) -> None:
        os.environ.pop("AI_ALLOW_PRIVATE_ENDPOINTS", None)
        os.environ.pop("AI_ALLOWED_LOCAL_ENDPOINTS", None)

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
            os.environ["AI_ALLOWED_LOCAL_ENDPOINTS"] = "192.168.1.10:11434"
            save_ai_settings(user["id"], {
                "provider": "local",
                "enabled": True,
                "base_url": "http://192.168.1.10:11434",
                "model": "model",
                "auth_type": "none",
            })
            os.environ.pop("AI_ALLOW_PRIVATE_ENDPOINTS", None)
            os.environ.pop("AI_ALLOWED_LOCAL_ENDPOINTS", None)
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
