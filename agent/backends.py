"""Model backends. Three, for three different reasons.

  api    the Anthropic SDK. What you will run, and what a reproduction should
         use. Needs ANTHROPIC_API_KEY.
  cli    shells out to the Claude Code CLI (`claude -p`). Runs on a Claude
         subscription with no API key. The published numbers were produced this
         way, which is stated in the README rather than hidden here.
  stub   no model at all: a deterministic keyword classifier. It exists so the
         eval pipeline -- loading, prompting, parsing, scoring, sweeping -- runs
         end to end in CI on every pull request with no secrets and no spend.
         It is a plumbing test, not a baseline claim. Its numbers are reported
         separately and are not the headline.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from typing import Protocol

from .prompt import SYSTEM


class Backend(Protocol):
    name: str
    modell: str

    def frage(self, nachricht: str, screenshot: bytes | None = None) -> str: ...


class ApiBackend:
    def __init__(self, modell: str = "claude-sonnet-5", max_tokens: int = 700):
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("pip install anthropic") from exc
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        self._client = anthropic.Anthropic()
        self.name = "api"
        self.modell = modell
        self._max_tokens = max_tokens

    def frage(self, nachricht: str, screenshot: bytes | None = None) -> str:
        import base64
        inhalt: list[dict] = []
        if screenshot:
            inhalt.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png",
                           "data": base64.b64encode(screenshot).decode()},
            })
        inhalt.append({"type": "text", "text": nachricht})
        antwort = self._client.messages.create(
            model=self.modell,
            max_tokens=self._max_tokens,
            system=SYSTEM,
            messages=[{"role": "user", "content": inhalt}],
        )
        return "".join(b.text for b in antwort.content if b.type == "text")


class CliBackend:
    """Claude Code in headless mode.

    The CLI has no separate system-prompt channel we can rely on across
    versions, so the system prompt is prepended to the message. MCP servers are
    switched off explicitly: this must be a single model call, not an agent with
    file access that could go and read the repo and quietly get the answer from
    somewhere the eval did not grant it.
    """

    def __init__(self, modell: str = "claude-sonnet-5", timeout: int = 180):
        if not shutil.which("claude"):
            raise RuntimeError("the `claude` CLI is not on PATH")
        self.name = "cli"
        self.modell = modell
        self._timeout = timeout

    def frage(self, nachricht: str, screenshot: bytes | None = None) -> str:
        if screenshot:
            raise NotImplementedError("the cli backend does not take images; use --backend api")
        prozess = subprocess.run(
            ["claude", "-p", SYSTEM + "\n\n---\n\n" + nachricht,
             "--output-format", "json", "--model", self.modell,
             "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}'],
            capture_output=True, text=True, encoding="utf-8", timeout=self._timeout,
        )
        if prozess.returncode != 0:
            raise RuntimeError(f"claude cli failed ({prozess.returncode}): {prozess.stderr[:400]}")
        huelle = json.loads(prozess.stdout)
        if huelle.get("is_error"):
            raise RuntimeError(f"claude cli reported an error: {str(huelle)[:400]}")
        return huelle["result"]


class StubBackend:
    """Keyword rules over the error text. No model, no network, no spend.

    Deliberately crude. Its job is to prove the pipeline runs, and to give the
    real model a floor to be compared against in the README.
    """

    name = "stub"
    modell = "keyword-rules"

    _REGELN: list[tuple[str, str, float]] = [
        (r"Executable doesn't exist|browserType\.launch|ENOENT|install playwright",
         "KAPUTTER_TEST", 0.92),
        (r"toHaveScreenshot|Screenshot comparison failed|pixels .* are different",
         "KAPUTTER_TEST", 0.72),
        (r"data-testid|getByTestId|strict mode violation|resolved to 0 elements",
         "KAPUTTER_TEST", 0.62),
        (r"Timeout .* exceeded|waiting for locator|exceeded while waiting",
         "FLAKE", 0.58),
        (r"toBe|toEqual|toHaveText|expected .* received", "PRODUKTFEHLER", 0.55),
    ]

    def frage(self, nachricht: str, screenshot: bytes | None = None) -> str:
        # A real retry-passed signal beats every keyword.
        if "failed and then passed without changing" in nachricht:
            return json.dumps({
                "klasse": "FLAKE", "konfidenz": 0.95,
                "begruendung": "The attempt log shows a pass on retry without a code change. "
                               "That is nondeterminism by definition.",
                "beleg": "failed and then passed without changing",
            })
        for muster, klasse, konfidenz in self._REGELN:
            treffer = re.search(muster, nachricht, re.IGNORECASE)
            if treffer:
                return json.dumps({
                    "klasse": klasse, "konfidenz": konfidenz,
                    "begruendung": f"Keyword rule matched {muster!r}. "
                                   "This backend does no reasoning.",
                    "beleg": treffer.group(0)[:120],
                })
        return json.dumps({
            "klasse": "PRODUKTFEHLER", "konfidenz": 0.30,
            "begruendung": "No rule matched. Falling back to the class whose cost of "
                           "being missed is highest.", "beleg": "",
        })


def baue_backend(name: str, modell: str | None = None) -> Backend:
    if name == "api":
        return ApiBackend(modell or "claude-sonnet-5")
    if name == "cli":
        return CliBackend(modell or "claude-sonnet-5")
    if name == "stub":
        return StubBackend()
    raise ValueError(f"unknown backend: {name} (api | cli | stub)")
