from __future__ import annotations

import contextlib
import unittest
from unittest import mock
from urllib.error import HTTPError

from financeiro import consultor
from financeiro.consultor import ConsultorError, prepare_local_analysis
from financeiro.consultor_provider import ConsultorProviderError, call_consultor_ai_provider

SETTINGS = {"consultor_enabled": True, "investor_profile": "moderado", "available": True}


def big_context() -> dict:
    return {"dados": "x" * 12_000}


def small_context() -> dict:
    return {"dados": "resumo curto"}


class PrepareLocalFallbackTest(unittest.TestCase):
    def prepare(self, order: list[str], context: dict):
        with mock.patch("financeiro.consultor.get_consultor_settings", return_value=SETTINGS), \
                mock.patch("financeiro.consultor.get_ai_execution_settings", return_value={"order": order}), \
                mock.patch("financeiro.consultor.build_analysis_context", return_value=context):
            return prepare_local_analysis(1, "ralos_financeiros")

    def test_oversized_prompt_skips_local_when_remote_is_allowed(self) -> None:
        with self.assertRaisesRegex(ConsultorError, "excede a janela da IA local"):
            self.prepare(["local", "remota", "deterministica"], big_context())

    def test_oversized_prompt_still_runs_local_when_remote_is_not_allowed(self) -> None:
        prepared = self.prepare(["local", "deterministica"], big_context())

        self.assertEqual(prepared["analysis_id"], "ralos_financeiros")

    def test_small_prompt_runs_local_even_when_remote_is_allowed(self) -> None:
        prepared = self.prepare(["local", "remota", "deterministica"], small_context())

        self.assertEqual(prepared["analysis_id"], "ralos_financeiros")
        self.assertLess(sum(len(m["content"]) for m in prepared["messages"]), consultor.LOCAL_PROMPT_CHAR_BUDGET)


class RemoteOutputBudgetTest(unittest.TestCase):
    def test_configured_700_tokens_are_raised_to_remote_floor(self) -> None:
        self.assertEqual(consultor.normalize_consultor_max_tokens(700), 700)
        self.assertEqual(
            max(consultor.normalize_consultor_max_tokens(700), consultor.CONSULTOR_REMOTE_MIN_OUTPUT_TOKENS),
            2500,
        )

    def test_configured_value_is_capped_at_remote_maximum(self) -> None:
        self.assertEqual(consultor.normalize_consultor_max_tokens(9000), consultor.CONSULTOR_REMOTE_MAX_OUTPUT_TOKENS)

    def test_configured_value_above_floor_is_respected(self) -> None:
        self.assertEqual(
            max(consultor.normalize_consultor_max_tokens(3000), consultor.CONSULTOR_REMOTE_MIN_OUTPUT_TOKENS),
            3000,
        )


class ProviderRetryTest(unittest.TestCase):
    AI_SETTINGS = {"provider": "google", "model": "gemini-test", "base_url": "https://generativelanguage.googleapis.com/v1beta"}

    def call(self, opener, text_extractor, payload: dict | None = None):
        with mock.patch("financeiro.consultor_provider.validate_ai_base_url"), \
                mock.patch("financeiro.consultor_provider.read_limited_json", return_value=payload or {"ok": True}), \
                mock.patch("time.sleep") as sleep:
            result = call_consultor_ai_provider(
                self.AI_SETTINGS,
                [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}],
                max_tokens=900,
                timeout_seconds=20,
                opener=opener,
                ssl_context_factory=lambda: None,
                text_extractor=text_extractor,
                request_builder=lambda settings, messages, max_tokens: {"url": "https://example.com/x", "body": {}, "headers": {}},
            )
        return result, sleep

    def test_transient_http_503_is_retried_until_success(self) -> None:
        calls = []

        def opener(request, timeout, context):
            calls.append(1)
            if len(calls) < 3:
                raise HTTPError(request.full_url, 503, "Service Unavailable", {}, None)
            return contextlib.nullcontext(object())

        result, sleep = self.call(opener, lambda payload, provider: "resposta")

        self.assertEqual(result, "resposta")
        self.assertEqual(len(calls), 3)
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [2, 4])

    def test_provider_error_payload_with_503_code_is_retried(self) -> None:
        calls = []

        def opener(request, timeout, context):
            calls.append(1)
            return contextlib.nullcontext(object())

        with self.assertRaises(ConsultorProviderError):
            self.call(opener, lambda payload, provider: "", payload={"error": {"code": 503, "status": "UNAVAILABLE"}})

        self.assertEqual(len(calls), 3)

    def test_timeout_is_not_retried(self) -> None:
        calls = []

        def opener(request, timeout, context):
            calls.append(1)
            raise TimeoutError("timed out")

        with self.assertRaises(ConsultorProviderError):
            self.call(opener, lambda payload, provider: "resposta")

        self.assertEqual(len(calls), 1)

    def test_non_transient_http_error_is_not_retried(self) -> None:
        calls = []

        def opener(request, timeout, context):
            calls.append(1)
            raise HTTPError(request.full_url, 400, "Bad Request", {}, None)

        with self.assertRaises(ConsultorProviderError):
            self.call(opener, lambda payload, provider: "resposta")

        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
