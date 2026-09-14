"""Verdict contract and the action policy.

Two things live here, and the split is deliberate:

  * what the MODEL produces  -> Verdict (klasse, konfidenz, begruendung, beleg)
  * what the SYSTEM decides  -> aktion, via `entscheide`

The model never picks the action. If it did, the confidence threshold could not
be swept offline: every new threshold would need a new inference run, and the
sweep in eval/ would cost 10x and drift between rows. Keeping policy out of the
model makes the sweep a pure function of stored predictions.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from typing import Any

KLASSEN = ("PRODUKTFEHLER", "KAPUTTER_TEST", "FLAKE")
AKTIONEN = ("RERUN", "TICKET", "ESKALATION_MENSCH")

# A FLAKE verdict needs a higher bar than the other two, because RERUN is the
# only action that can make a failure disappear without a human ever seeing it.
# A wrong TICKET wastes someone's morning; a wrong RERUN ships the bug.
FLAKE_AUFSCHLAG = 0.10


class VerdictError(ValueError):
    """The model returned something that is not a usable verdict."""


@dataclass(frozen=True)
class Verdict:
    klasse: str
    konfidenz: float
    begruendung: str
    beleg: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def entscheide(klasse: str, konfidenz: float, schwelle: float,
               flake_aufschlag: float = FLAKE_AUFSCHLAG) -> str:
    """Map (class, confidence) to an action under a given threshold.

    Below the threshold the agent does not decide -- it hands over. That is the
    whole point of the thing: an agent that knows when it does not know.
    """
    if not 0.0 <= schwelle <= 1.0:
        raise ValueError(f"schwelle out of range: {schwelle}")
    if klasse not in KLASSEN:
        raise ValueError(f"unknown klasse: {klasse}")

    noetig = schwelle + flake_aufschlag if klasse == "FLAKE" else schwelle
    if konfidenz < noetig:
        return "ESKALATION_MENSCH"
    return "RERUN" if klasse == "FLAKE" else "TICKET"


_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


def parse_verdict(rohtext: str) -> Verdict:
    """Parse a model reply into a Verdict, or raise VerdictError.

    Tolerant about wrapping (code fences, a stray sentence before the JSON),
    strict about content. A malformed verdict is never silently repaired into a
    class -- it is an error, and the eval counts it as such.
    """
    if not rohtext or not rohtext.strip():
        raise VerdictError("empty model reply")

    text = rohtext.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    treffer = _JSON_BLOCK.search(text)
    if not treffer:
        raise VerdictError(f"no JSON object in reply: {rohtext[:200]!r}")

    try:
        daten = json.loads(treffer.group(0))
    except json.JSONDecodeError as exc:
        raise VerdictError(f"invalid JSON: {exc}") from exc

    if not isinstance(daten, dict):
        raise VerdictError("JSON payload is not an object")

    fehlend = [f for f in ("klasse", "konfidenz", "begruendung") if f not in daten]
    if fehlend:
        raise VerdictError(f"missing fields: {', '.join(fehlend)}")

    klasse = str(daten["klasse"]).strip().upper()
    if klasse not in KLASSEN:
        raise VerdictError(f"unknown klasse: {daten['klasse']!r}")

    try:
        konfidenz = float(daten["konfidenz"])
    except (TypeError, ValueError) as exc:
        raise VerdictError(f"konfidenz not a number: {daten['konfidenz']!r}") from exc
    if not 0.0 <= konfidenz <= 1.0:
        raise VerdictError(f"konfidenz out of range: {konfidenz}")

    return Verdict(
        klasse=klasse,
        konfidenz=konfidenz,
        begruendung=str(daten["begruendung"]).strip(),
        beleg=str(daten.get("beleg", "")).strip(),
    )
