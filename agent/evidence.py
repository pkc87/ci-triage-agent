"""Load a case directory into the evidence bundle the model gets to see.

Everything the agent knows comes through here. Two rules govern this file:

  1. Nothing is invented. A missing artefact is reported as missing, in the
     prompt, in those words. The model is told what it does not have so it can
     lower its confidence instead of hallucinating a reason.
  2. Everything is budgeted. Traces and diffs can run to megabytes; a CI triage
     agent that costs a dollar a failure will not be deployed. Truncation is
     explicit and visible to the model.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

# Character budgets. Chosen by looking at the corpus, not by taste: the largest
# real diff in eval/cases is ~11k chars, the longest trace excerpt ~6k.
BUDGET_FEHLER = 6_000
BUDGET_DIFF = 14_000
BUDGET_TRACE = 8_000
BUDGET_LOG = 8_000


def entferne_ansi(text: str) -> str:
    return ANSI.sub("", text)


def kuerze(text: str, budget: int, was: str) -> str:
    """Truncate in the middle: the head and the tail of a diff or trace both
    carry signal, the middle usually does not."""
    if len(text) <= budget:
        return text
    kopf = budget * 2 // 3
    schwanz = budget - kopf
    entfernt = len(text) - budget
    return (text[:kopf]
            + f"\n\n[... {entfernt} characters of {was} omitted ...]\n\n"
            + text[-schwanz:])


@dataclass
class Fall:
    id: str
    quelle: str
    pfad: Path
    daten: dict
    diff: str | None = None
    trace: str | None = None
    ci_log: str | None = None
    screenshot: Path | None = None
    fehlend: list[str] = field(default_factory=list)

    @property
    def versuche_text(self) -> str:
        versuche = self.daten.get("versuche") or []
        if not versuche:
            return "no attempt data recorded"
        teile = [f"attempt {v.get('nr', '?')}: {v.get('status', '?')}" for v in versuche]
        text = ", ".join(teile)
        stati = [v.get("status") for v in versuche]
        if "passed" in stati and "failed" in stati:
            text += "  <- the same code failed and then passed without changing"
        return text


def lade_fall(pfad: str | Path) -> Fall:
    pfad = Path(pfad)
    fall_json = pfad / "fall.json"
    if not fall_json.exists():
        raise FileNotFoundError(f"{fall_json} missing -- not a case directory")
    daten = json.loads(fall_json.read_text(encoding="utf-8"))

    def lies(name: str, budget: int) -> str | None:
        p = pfad / name
        if not p.exists():
            return None
        return kuerze(entferne_ansi(p.read_text(encoding="utf-8", errors="replace")),
                      budget, name)

    fall = Fall(
        id=daten.get("id", pfad.name),
        quelle=daten.get("quelle", "unbekannt"),
        pfad=pfad,
        daten=daten,
        diff=lies("diff.patch", BUDGET_DIFF),
        trace=lies("trace.txt", BUDGET_TRACE),
        ci_log=lies("log_excerpt.txt", BUDGET_LOG),
    )
    schuss = pfad / "screenshot.png"
    fall.screenshot = schuss if schuss.exists() else None

    for name, wert in (("diff", fall.diff), ("trace", fall.trace),
                       ("screenshot", fall.screenshot)):
        if wert is None:
            fall.fehlend.append(name)
    return fall


def als_prompt(fall: Fall, mit_screenshot: bool = False) -> str:
    """Render the bundle as the user-message text."""
    d = fall.daten
    zeilen: list[str] = []
    a = zeilen.append

    a("## Failing test")
    a(f"title:  {d.get('test_titel', '(unknown)')}")
    a(f"file:   {d.get('test_datei', '(unknown)')}:{d.get('test_zeile', '?')}")
    a(f"repo:   {d.get('repo', '(unknown)')}")
    a(f"duration: {d.get('dauer_ms', '?')} ms")
    a(f"attempts: {fall.versuche_text}")
    kontext = d.get("kontext") or {}
    if kontext:
        a(f"branch: {kontext.get('branch', '(unknown)')}   commit: {kontext.get('commit', '(unknown)')}")

    a("")
    a("## Error")
    a("```")
    a(kuerze(entferne_ansi(str(d.get("fehlermeldung", "")).strip()), BUDGET_FEHLER, "error text"))
    a("```")

    stack = entferne_ansi(str(d.get("stack", "")).strip())
    if stack:
        a("")
        a("## Stack / code frame")
        a("```")
        a(kuerze(stack, 3_000, "stack"))
        a("```")

    if fall.trace:
        a("")
        a("## Trace (action log extracted from trace.zip)")
        a("```")
        a(fall.trace)
        a("```")

    if fall.ci_log:
        a("")
        a("## CI log excerpt")
        a("```")
        a(fall.ci_log)
        a("```")

    if fall.diff:
        a("")
        a("## Diff of the change under test")
        a("```diff")
        a(fall.diff)
        a("```")

    if fall.fehlend:
        a("")
        a("## Evidence NOT available for this case")
        a(", ".join(fall.fehlend)
          + ". Do not speculate about what these would have shown; if the "
            "decision depends on them, say so and lower your confidence.")

    if mit_screenshot and fall.screenshot:
        a("")
        a("## Screenshot")
        a("The failure screenshot is attached as an image.")

    return "\n".join(zeilen)
