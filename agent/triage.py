"""One failing test in, one verdict plus an action out."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from .backends import Backend
from .evidence import Fall, als_prompt, lade_fall
from .prompt import baue_nachricht
from .schema import FLAKE_AUFSCHLAG, Verdict, VerdictError, entscheide, parse_verdict


@dataclass
class Ergebnis:
    fall_id: str
    verdict: Verdict | None
    aktion: str
    fehler: str | None = None
    dauer_ms: int = 0
    versuche_modell: int = 1
    rohtext: str = ""

    def as_dict(self) -> dict:
        return {
            "fall_id": self.fall_id,
            "klasse": self.verdict.klasse if self.verdict else None,
            "konfidenz": self.verdict.konfidenz if self.verdict else None,
            "begruendung": self.verdict.begruendung if self.verdict else None,
            "beleg": self.verdict.beleg if self.verdict else None,
            "aktion": self.aktion,
            "fehler": self.fehler,
            "dauer_ms": self.dauer_ms,
            "versuche_modell": self.versuche_modell,
        }


def triagiere(fall: Fall | str | Path,
              backend: Backend,
              schwelle: float = 0.70,
              flake_aufschlag: float = FLAKE_AUFSCHLAG,
              mit_screenshot: bool = False,
              max_versuche: int = 2) -> Ergebnis:
    """Classify one failure and decide what to do with it.

    A verdict the parser rejects is retried once -- models occasionally wrap
    JSON in prose -- and then given up on. A give-up is NOT quietly turned into
    a class: it escalates to a human and is counted as a parse failure in the
    eval. Silently defaulting an unparseable answer to some class would put
    noise straight into the precision number.
    """
    if not isinstance(fall, Fall):
        fall = lade_fall(fall)

    nachricht = baue_nachricht(als_prompt(fall, mit_screenshot=mit_screenshot))
    bild = None
    if mit_screenshot and fall.screenshot:
        bild = fall.screenshot.read_bytes()

    start = time.monotonic()
    letzter_fehler = ""
    rohtext = ""
    for versuch in range(1, max_versuche + 1):
        try:
            rohtext = backend.frage(nachricht, screenshot=bild)
            verdict = parse_verdict(rohtext)
        except VerdictError as exc:
            letzter_fehler = f"unparseable verdict: {exc}"
            continue
        except Exception as exc:  # backend/transport failure
            letzter_fehler = f"backend error: {type(exc).__name__}: {exc}"
            time.sleep(1.5 * versuch)
            continue
        return Ergebnis(
            fall_id=fall.id,
            verdict=verdict,
            aktion=entscheide(verdict.klasse, verdict.konfidenz, schwelle, flake_aufschlag),
            dauer_ms=int((time.monotonic() - start) * 1000),
            versuche_modell=versuch,
            rohtext=rohtext,
        )

    return Ergebnis(
        fall_id=fall.id,
        verdict=None,
        aktion="ESKALATION_MENSCH",
        fehler=letzter_fehler,
        dauer_ms=int((time.monotonic() - start) * 1000),
        versuche_modell=max_versuche,
        rohtext=rohtext,
    )
