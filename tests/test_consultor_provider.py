import json
import os
import unittest
from unittest import mock
from urllib.error import HTTPError, URLError

from financeiro import consultor, consultor_provider


class ConsultorProviderContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = {
            "provider": "openai", "base_url": "http://127.0.0.1:1234",
            "model": "test-model", "api_key": "test-key", "auth_type": "bearer",
        }
        self.messages = consultor.build_ai_messages("Prompt", {"total_cents": 123})
        os.environ["AI_ALLOW_PRIVATE_ENDPOINTS"] = "true"

    def test_facade_and_adapter_preserve_all_request_shapes(self) -> None:
        for provider in ("openai", "custom", "google", "anthropic"):
            with self.subTest(provider=provider):
                settings = {**self.settings, "provider": provider}
                self.assertEqual(
                    consultor.build_consultor_ai_request(settings, self.messages, max_tokens=700),
                    consultor_provider.build_consultor_ai_request(settings, self.messages, max_tokens=700),
                )

    def test_facade_injects_late_bound_transport_and_helpers(self) -> None:
        with mock.patch.object(consultor, "ai_urlopen") as opener, \
                mock.patch.object(consultor, "ai_ssl_context", return_value="ssl-context") as ssl, \
                mock.patch.object(consultor, "extract_summary_text", return_value="Resposta") as extract, \
                mock.patch.object(consultor, "build_consultor_ai_request", wraps=consultor.build_consultor_ai_request) as builder:
            opener.return_value.__enter__.return_value.read.return_value = b'{"choices": []}'
            self.assertEqual(consultor.call_consultor_ai_provider(
                self.settings, self.messages, max_tokens=700, timeout_seconds=35,
            ), "Resposta")
            request = opener.call_args.args[0]
            self.assertEqual(request.get_method(), "POST")
            self.assertEqual(json.loads(request.data)["max_tokens"], 700)
            self.assertEqual(opener.call_args.kwargs, {"timeout": 35, "context": "ssl-context"})
            ssl.assert_called_once_with()
            extract.assert_called_once_with({"choices": []}, provider="openai")
            builder.assert_called_once_with(self.settings, self.messages, max_tokens=700)

    def test_transport_failures_keep_public_error_type_and_message(self) -> None:
        failures = [TimeoutError("private detail"), URLError("private detail"),
                    OSError("private detail"), HTTPError("http://127.0.0.1:1234", 503, "private detail", {}, None)]
        for failure in failures:
            with self.subTest(failure=type(failure).__name__), \
                    mock.patch.object(consultor, "ai_urlopen", side_effect=failure), \
                    mock.patch.object(consultor, "ai_ssl_context", return_value=None):
                with self.assertRaises(consultor.ConsultorError) as raised:
                    consultor.call_consultor_ai_provider(self.settings, self.messages, max_tokens=700, timeout_seconds=20)
                self.assertEqual(str(raised.exception), "O Consultor esta indisponivel no momento.")

    def test_invalid_json_and_empty_output_are_standardized(self) -> None:
        for raw_response in (b'not-json', b'{"choices": []}'):
            with self.subTest(raw_response=raw_response), \
                    mock.patch.object(consultor, "ai_urlopen") as opener, \
                    mock.patch.object(consultor, "ai_ssl_context", return_value=None):
                opener.return_value.__enter__.return_value.read.return_value = raw_response
                with self.assertRaises(consultor.ConsultorError):
                    consultor.call_consultor_ai_provider(self.settings, self.messages, max_tokens=700, timeout_seconds=20)

    def test_invalid_configuration_preserves_public_error(self) -> None:
        with self.assertRaises(consultor.ConsultorError):
            consultor.build_consultor_ai_request({}, self.messages, max_tokens=700)
        with self.assertRaises(consultor_provider.ConsultorProviderError):
            consultor_provider.build_consultor_ai_request({}, self.messages, max_tokens=700)
