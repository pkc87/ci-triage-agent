"""The api backend is the path the README tells people to use, so it gets tested.

No network: the anthropic client is replaced with a recorder. What is checked is
the part that silently breaks -- that the system prompt is sent as a system
prompt, that a screenshot becomes a real image block ahead of the text, and that
the reply is unwrapped into a plain string.
"""
import pathlib
import sys
import types

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from agent.backends import StubBackend, baue_backend  # noqa: E402
from agent.prompt import SYSTEM  # noqa: E402


class _Block:
    def __init__(self, text):
        self.type, self.text = "text", text


class _Recorder:
    """Stands in for anthropic.Anthropic()."""
    def __init__(self):
        self.gesehen = None
        self.messages = types.SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.gesehen = kwargs
        return types.SimpleNamespace(content=[_Block('{"klasse":"FLAKE","konfidenz":0.8,'
                                                    '"begruendung":"x","beleg":"y"}')])


@pytest.fixture
def api_backend(monkeypatch):
    rec = _Recorder()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-a-real-key")
    fake = types.ModuleType("anthropic")
    fake.Anthropic = lambda *a, **k: rec
    monkeypatch.setitem(sys.modules, "anthropic", fake)
    from agent.backends import ApiBackend
    return ApiBackend(modell="claude-sonnet-5"), rec


def test_api_sendet_system_prompt_getrennt(api_backend):
    backend, rec = api_backend
    backend.frage("triage this")
    assert rec.gesehen["system"] == SYSTEM
    assert rec.gesehen["model"] == "claude-sonnet-5"
    # the evidence must not be smuggled into the system prompt
    assert "triage this" not in rec.gesehen["system"]


def test_api_haengt_screenshot_vor_den_text(api_backend):
    backend, rec = api_backend
    backend.frage("triage this", screenshot=b"\x89PNG\r\n\x1a\nfake")
    inhalt = rec.gesehen["messages"][0]["content"]
    assert inhalt[0]["type"] == "image"
    assert inhalt[0]["source"]["media_type"] == "image/png"
    assert inhalt[1]["type"] == "text"


def test_api_ohne_screenshot_schickt_kein_bild(api_backend):
    backend, rec = api_backend
    backend.frage("triage this")
    inhalt = rec.gesehen["messages"][0]["content"]
    assert [b["type"] for b in inhalt] == ["text"]


def test_api_gibt_reinen_text_zurueck(api_backend):
    backend, _ = api_backend
    assert backend.frage("x").startswith('{"klasse"')


def test_api_ohne_schluessel_faellt_sofort_auf(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    fake = types.ModuleType("anthropic")
    fake.Anthropic = lambda *a, **k: None
    monkeypatch.setitem(sys.modules, "anthropic", fake)
    from agent.backends import ApiBackend
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        ApiBackend()


def test_stub_nimmt_den_retry_pass_vor_jedem_schluesselwort():
    # The error text says "Executable doesn't exist", which the keyword rules
    # would call KAPUTTER_TEST. A real retry-pass outranks it.
    antwort = StubBackend().frage(
        "attempts: attempt 1: failed, attempt 2: passed  "
        "<- the same code failed and then passed without changing\n"
        "Error: Executable doesn't exist at /x")
    assert '"klasse": "FLAKE"' in antwort


def test_unbekanntes_backend_fliegt_auf():
    with pytest.raises(ValueError, match="unknown backend"):
        baue_backend("telepathy")
