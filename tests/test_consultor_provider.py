import json
import os
import unittest
from datetime import date
from unittest import mock
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit

from financeiro import consultor, consultor_provider


class ConsultorProviderContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = {
            "provider": "openai", "base_url": "http://127.0.0.1:1234",
            "model": "test-model", "api_key": "test-key", "auth_type": "bearer",
        }
        self.messages = consultor.build_ai_messages("Prompt", {"total_cents": 123})
        os.environ["AI_ALLOW_PRIVATE_ENDPOINTS"] = "true"
        os.environ["AI_ALLOWED_LOCAL_ENDPOINTS"] = "127.0.0.1:1234"

    def tearDown(self) -> None:
        os.environ.pop("AI_ALLOW_PRIVATE_ENDPOINTS", None)
        os.environ.pop("AI_ALLOWED_LOCAL_ENDPOINTS", None)

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

    def test_empty_google_response_is_classified_without_exposing_payload(self) -> None:
        settings = {
            "provider": "google",
            "base_url": "https://generativelanguage.googleapis.com/v1beta",
            "model": "gemini-test",
            "api_key": "test-key",
        }
        response_payload = {
            "candidates": [{
                "finishReason": "MAX_TOKENS",
                "content": {"parts": []},
            }],
            "usageMetadata": {
                "promptTokenCount": 2317,
                "candidatesTokenCount": 0,
                "thoughtsTokenCount": 512,
                "totalTokenCount": 2829,
            },
        }
        with mock.patch.object(consultor_provider, "validate_ai_base_url"), \
                mock.patch.object(consultor_provider, "ai_urlopen") as opener:
            opener.return_value.__enter__.return_value.read.return_value = json.dumps(
                response_payload
            ).encode()
            with self.assertRaises(consultor_provider.ConsultorProviderError) as raised:
                consultor_provider.call_consultor_ai_provider(
                    settings,
                    self.messages,
                    max_tokens=700,
                    timeout_seconds=20,
                    ssl_context_factory=lambda: None,
                )

        self.assertEqual(raised.exception.reason, "candidate_without_text")
        self.assertEqual(raised.exception.diagnostics, {
            "response_reason": "candidate_without_text",
            "candidate_count": 1,
            "candidate_part_count": 0,
            "text_part_count": 0,
            "finish_reasons": "MAX_TOKENS",
            "prompt_tokens": 2317,
            "candidate_tokens": 0,
            "thought_tokens": 512,
            "total_tokens": 2829,
            "request_model": "gemini-test",
            "request_url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-test:generateContent",
        })

    def test_google_blocked_response_diagnostics_omit_response_content(self) -> None:
        diagnostics = consultor_provider.describe_empty_ai_response({
            "promptFeedback": {"blockReason": "SAFETY", "safetyRatings": [{"category": "OTHER"}]},
            "candidates": [],
            "private": "must not be copied",
        }, "google")

        self.assertEqual(diagnostics, {
            "response_reason": "prompt_blocked",
            "candidate_count": 0,
            "candidate_part_count": 0,
            "text_part_count": 0,
            "prompt_block_reason": "SAFETY",
        })

    def test_google_error_payload_logs_only_allowlisted_status_and_code(self) -> None:
        payload = {
            "error": {
                "code": 503,
                "status": "UNAVAILABLE",
                "message": "private provider message",
            },
            "private": "private response content",
        }
        diagnostics = consultor_provider.describe_empty_ai_response(payload, "google")

        self.assertEqual(diagnostics, {
            "response_reason": "provider_error_payload",
            "candidate_count": 0,
            "candidate_part_count": 0,
            "text_part_count": 0,
            "provider_code": 503,
            "provider_status": "UNAVAILABLE",
        })
        error = consultor_provider.ConsultorProviderError(
            "unavailable",
            diagnostics=diagnostics,
        )
        logged = consultor_provider.format_safe_provider_diagnostics(error)
        self.assertIn("provider_code=503", logged)
        self.assertIn("provider_status=UNAVAILABLE", logged)
        self.assertNotIn("private", logged)
        self.assertEqual(
            consultor_provider.format_safe_provider_diagnostics({
                "response_reason": "private account contents",
                "finish_reasons": "PRIVATE ACCOUNT",
                "provider_status": "private account status",
            }),
            "finish_reasons=OTHER",
        )

    def test_invalid_configuration_preserves_public_error(self) -> None:
        with self.assertRaises(consultor.ConsultorError):
            consultor.build_consultor_ai_request({}, self.messages, max_tokens=700)
        with self.assertRaises(consultor_provider.ConsultorProviderError):
            consultor_provider.build_consultor_ai_request({}, self.messages, max_tokens=700)

    def test_market_research_requests_are_provider_native_and_user_data_free(self) -> None:
        configurations = {
            "openai": {
                "base_url": "https://api.openai.com/v1",
                "expected_path": "/v1/responses",
                "expected_tool": "web_search",
            },
            "google": {
                "base_url": "https://generativelanguage.googleapis.com/v1beta",
                "expected_path": "/v1beta/models/test-model:generateContent",
                "expected_tool": "google_search",
            },
            "anthropic": {
                "base_url": "https://api.anthropic.com/v1",
                "expected_path": "/v1/messages",
                "expected_tool": "web_search_20250305",
            },
        }
        for provider, configuration in configurations.items():
            with self.subTest(provider=provider):
                with mock.patch.object(consultor_provider, "validate_ai_base_url", side_effect=lambda value: value):
                    request = consultor_provider.build_market_research_request({
                        **configuration,
                        "provider": provider,
                        "model": "test-model",
                        "api_key": "test-key",
                    })
                self.assertIsNotNone(request)
                self.assertEqual(urlsplit(request["url"]).path, configuration["expected_path"])
                body_text = json.dumps(request["body"], ensure_ascii=False).lower()
                for private_value in ("patrimonio", "saldo do usuario", "perfil complementar", "posicoes do usuario"):
                    self.assertNotIn(private_value, body_text)
                if provider == "google":
                    self.assertIn("google_search", request["body"]["tools"][0])
                else:
                    self.assertIn(configuration["expected_tool"], json.dumps(request["body"]))

        with mock.patch.object(consultor_provider, "validate_ai_base_url", side_effect=lambda value: value):
            self.assertIsNone(consultor_provider.build_market_research_request({
                "provider": "custom", "base_url": "https://api.example.com/v1",
                "model": "model", "api_key": "key",
            }))
            self.assertIsNone(consultor_provider.build_market_research_request({
                "provider": "openai", "base_url": "https://proxy.example.com/v1",
                "model": "model", "api_key": "key",
            }))

    def test_market_research_requires_dated_summary_and_https_sources(self) -> None:
        response = {
            "output": [{
                "type": "message",
                "content": [{
                    "type": "output_text",
                    "text": "O cenário indica incerteza sobre juros e inflação.",
                    "annotations": [
                        {"type": "url_citation", "title": "Banco Central", "url": "https://bcb.gov.br/noticia"},
                        {"type": "url_citation", "title": "Inválida", "url": "http://unsafe.example/article"},
                    ],
                }],
            }],
        }
        result = consultor_provider.extract_market_research(response, "openai")

        self.assertEqual(result["summary"], "O cenário indica incerteza sobre juros e inflação.")
        self.assertEqual(result["sources"], [{
            "id": "C1", "title": "Banco Central", "url": "https://bcb.gov.br/noticia",
        }])
        self.assertIsNone(consultor_provider.extract_market_research({
            "output": [{"type": "message", "content": [{"type": "output_text", "text": "Sem fontes."}]}],
        }, "openai"))

    def test_market_research_transport_sends_only_static_topic_and_returns_date(self) -> None:
        payload = {
            "output": [{
                "type": "message",
                "content": [{
                    "type": "output_text",
                    "text": "Cenário de juros incerto.",
                    "annotations": [{"type": "url_citation", "title": "BCB", "url": "https://bcb.gov.br"}],
                }],
            }],
        }
        with mock.patch.object(consultor_provider, "ai_urlopen") as opener, \
                mock.patch("financeiro.ai_summary.ai_ssl_context", return_value=None), \
                mock.patch.object(consultor_provider, "validate_ai_base_url", side_effect=lambda value: value):
            opener.return_value.__enter__.return_value.read.return_value = json.dumps(payload).encode()
            result = consultor_provider.call_consultor_market_research(
                {
                    "provider": "openai",
                    "base_url": "https://api.openai.com/v1",
                    "model": "gpt-test",
                    "api_key": "test-key",
                },
                timeout_seconds=20,
                today=date(2026, 10, 11),
            )

        request = opener.call_args.args[0]
        request_body = json.loads(request.data)
        self.assertEqual(set(request_body), {"model", "tools", "input", "max_output_tokens"})
        self.assertNotIn("portfolio", json.dumps(request_body).lower())
        self.assertNotIn("profile", json.dumps(request_body).lower())
        self.assertEqual(result["researched_at"], "2026-10-11")
