import io
from http.client import IncompleteRead
import unittest

from financeiro.outbound_json import OutboundJsonError, read_limited_json


class Response(io.BytesIO):
    def __init__(self, body: bytes, content_length=None):
        super().__init__(body)
        self.headers = {}
        if content_length is not None:
            self.headers["Content-Length"] = content_length


class ExternalJsonTests(unittest.TestCase):
    def test_accepts_valid_json_at_limit(self):
        body = b'{"ok":true}'
        self.assertEqual(read_limited_json(Response(body), max_bytes=len(body)), {"ok": True})

    def test_rejects_actual_body_over_limit_without_content_length(self):
        with self.assertRaises(OutboundJsonError):
            read_limited_json(Response(b'{"value":123}'), max_bytes=5)

    def test_rejects_declared_body_before_reading(self):
        response = Response(b'{}', content_length="999")
        response.read = unittest.mock.Mock(wraps=response.read)
        with self.assertRaises(OutboundJsonError):
            read_limited_json(response, max_bytes=10)
        response.read.assert_not_called()

    def test_ignores_untrusted_length_and_keeps_effective_limit(self):
        for declared in ("invalid", "-1", "2"):
            with self.subTest(declared=declared), self.assertRaises(OutboundJsonError):
                read_limited_json(Response(b'{"value":123}', declared), max_bytes=5)

    def test_rejects_invalid_json_and_utf8(self):
        for body in (b"invalid", b'"\xff"'):
            with self.subTest(body=body), self.assertRaises(OutboundJsonError):
                read_limited_json(Response(body), max_bytes=100)

    def test_wraps_truncated_http_response(self):
        response = Response(b"{}")
        response.read = unittest.mock.Mock(side_effect=IncompleteRead(b"{", 10))
        with self.assertRaises(OutboundJsonError):
            read_limited_json(response, max_bytes=100)

    def test_rejects_excessively_nested_json(self):
        body = (b"[" * 100_000) + (b"]" * 100_000)
        with self.assertRaises(OutboundJsonError):
            read_limited_json(Response(body), max_bytes=len(body))

    def test_rejects_integer_beyond_parser_safety_limit(self):
        body = b"1" * 10_000
        with self.assertRaises(OutboundJsonError):
            read_limited_json(Response(body), max_bytes=len(body))


if __name__ == "__main__":
    unittest.main()
