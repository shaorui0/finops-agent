"""LLM client with record / replay / live modes.

  replay  (default)  read eval/cassettes/<sha256(model + prompt)>.json; a missing cassette is an error
  record             call `claude -p`, save the full response (text, usage, cost, duration) as a cassette;
                     an existing cassette is reused, set FINOPS_LLM_FORCE=1 to overwrite
  live               call `claude -p`, do not touch cassettes

Select with the FINOPS_LLM_MODE environment variable. Replay needs no network and no API key, which is
what keeps `make eval` and CI deterministic. Every call returns the numbers the trace needs
(tokens_in, tokens_out, latency_ms, cost_usd); in replay they are the recorded values.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASSETTE_DIR = ROOT / "eval" / "cassettes"
DEFAULT_MODEL = "sonnet"
SYSTEM_PROMPT = "You are a JSON-only function. Reply with exactly one JSON object and nothing else."
MODES = ("replay", "record", "live")


class LLMError(RuntimeError):
    pass


class CassetteMissing(LLMError):
    pass


@dataclass
class LLMResult:
    text: str
    tokens_in: int
    tokens_out: int
    latency_ms: float      # recorded model latency (replay returns the recorded value)
    cost_usd: float        # recorded cost (replay returns the recorded value)
    key: str
    mode: str
    model: str


def cassette_key(model: str, prompt: str) -> str:
    return hashlib.sha256((model + "\n" + prompt).encode()).hexdigest()


def parse_claude_json(stdout: str) -> dict:
    """Map the `claude -p --output-format json` payload to cassette fields."""
    d = json.loads(stdout)
    if d.get("is_error") or d.get("subtype", "success") != "success":
        raise LLMError(f"claude reported an error: {str(d.get('result'))[:300]}")
    u = d.get("usage", {})
    tokens_in = int(u.get("input_tokens", 0)) + int(u.get("cache_creation_input_tokens", 0)) + int(u.get("cache_read_input_tokens", 0))
    return {"text": d["result"], "tokens_in": tokens_in, "tokens_out": int(u.get("output_tokens", 0)),
            "latency_ms": float(d.get("duration_ms", 0)), "cost_usd": float(d.get("total_cost_usd", 0.0)),
            "usage": u}


class LLMClient:
    def __init__(self, mode: str | None = None, model: str = DEFAULT_MODEL, cassette_dir: Path | None = None):
        self.mode = (mode or os.environ.get("FINOPS_LLM_MODE") or "replay").strip()
        if self.mode not in MODES:
            raise LLMError(f"FINOPS_LLM_MODE must be one of {MODES}, got {self.mode!r}")
        self.model = model
        self.dir = Path(cassette_dir or CASSETTE_DIR)

    def path(self, key: str) -> Path:
        return self.dir / f"{key}.json"

    def complete(self, prompt: str) -> LLMResult:
        key = cassette_key(self.model, prompt)
        p = self.path(key)
        force = os.environ.get("FINOPS_LLM_FORCE") == "1"
        if self.mode == "replay" or (self.mode == "record" and p.exists() and not force):
            if not p.exists():
                raise CassetteMissing(f"no cassette {key[:12]} for model={self.model} (prompt starts: {prompt[:60]!r}); "
                                      f"re-record with FINOPS_LLM_MODE=record")
            return self._from_cassette(json.loads(p.read_text()), key)
        rec = self._call(prompt)
        if self.mode == "record":
            self.dir.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps({"model": self.model, "key": key, "prompt": prompt, **rec}, indent=2, ensure_ascii=False))
        return self._from_cassette(rec, key)

    def _from_cassette(self, c: dict, key: str) -> LLMResult:
        return LLMResult(c["text"], c["tokens_in"], c["tokens_out"], c["latency_ms"], c["cost_usd"], key, self.mode, self.model)

    def _call(self, prompt: str) -> dict:
        cmd = ["claude", "-p", "--model", self.model, "--output-format", "json", "--tools", "",
               "--system-prompt", SYSTEM_PROMPT, "--setting-sources", "", "--disable-slash-commands",
               "--no-session-persistence", prompt]
        t0 = time.time()
        with tempfile.TemporaryDirectory() as cwd:   # no project CLAUDE.md in the model's context
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=cwd)
        if proc.returncode != 0:
            raise LLMError(f"claude exited {proc.returncode}: {proc.stderr[:300]}")
        rec = parse_claude_json(proc.stdout)
        rec["wall_ms"] = round((time.time() - t0) * 1000, 1)
        return rec
