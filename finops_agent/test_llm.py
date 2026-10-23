import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from finops_agent.llm import CassetteMissing, LLMClient, LLMError, cassette_key, parse_claude_json

CLAUDE_PAYLOAD = {"type": "result", "subtype": "success", "is_error": False, "result": "{\"a\": 1}", "duration_ms": 2767,
                  "total_cost_usd": 0.004024, "usage": {"input_tokens": 2, "cache_creation_input_tokens": 565,
                                                        "cache_read_input_tokens": 10, "output_tokens": 176}}
REC = {"text": "{\"verdict\": \"not_waste\"}", "tokens_in": 100, "tokens_out": 20, "latency_ms": 1500.0, "cost_usd": 0.01, "usage": {}}


class LLMTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_key_depends_on_model_and_prompt(self):
        self.assertEqual(cassette_key("m", "p"), cassette_key("m", "p"))
        self.assertNotEqual(cassette_key("m", "p"), cassette_key("m2", "p"))
        self.assertNotEqual(cassette_key("m", "p"), cassette_key("m", "p2"))

    def test_parse_claude_json_fields(self):
        r = parse_claude_json(json.dumps(CLAUDE_PAYLOAD))
        self.assertEqual((r["tokens_in"], r["tokens_out"], r["latency_ms"], r["cost_usd"]), (577, 176, 2767.0, 0.004024))
        self.assertEqual(r["text"], "{\"a\": 1}")

    def test_parse_claude_json_error(self):
        with self.assertRaises(LLMError):
            parse_claude_json(json.dumps({**CLAUDE_PAYLOAD, "is_error": True}))

    def test_replay_missing_cassette_is_an_error(self):
        with self.assertRaises(CassetteMissing):
            LLMClient("replay", cassette_dir=self.dir).complete("never recorded")

    def test_replay_never_calls_the_model(self):
        c = LLMClient("replay", cassette_dir=self.dir)
        c.path(cassette_key(c.model, "p")).write_text(json.dumps(REC))
        with mock.patch.object(LLMClient, "_call", side_effect=AssertionError("network")):
            r = c.complete("p")
        self.assertEqual((r.tokens_in, r.tokens_out, r.latency_ms, r.cost_usd, r.mode), (100, 20, 1500.0, 0.01, "replay"))

    def test_record_writes_then_reuses(self):
        c = LLMClient("record", cassette_dir=self.dir)
        with mock.patch.object(LLMClient, "_call", return_value=REC) as call:
            c.complete("p")
            c.complete("p")
        self.assertEqual(call.call_count, 1)
        saved = json.loads(c.path(cassette_key(c.model, "p")).read_text())
        self.assertEqual((saved["prompt"], saved["cost_usd"]), ("p", 0.01))
        with mock.patch.dict(os.environ, {"FINOPS_LLM_FORCE": "1"}), mock.patch.object(LLMClient, "_call", return_value=REC) as call:
            c.complete("p")
        self.assertEqual(call.call_count, 1)

    def test_live_does_not_write(self):
        c = LLMClient("live", cassette_dir=self.dir)
        with mock.patch.object(LLMClient, "_call", return_value=REC):
            c.complete("p")
        self.assertEqual(list(self.dir.glob("*.json")), [])

    def test_bad_mode(self):
        with self.assertRaises(LLMError):
            LLMClient("yolo")

    def test_default_mode_is_replay(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("FINOPS_LLM_MODE", None)
            self.assertEqual(LLMClient().mode, "replay")


if __name__ == "__main__":
    unittest.main()
