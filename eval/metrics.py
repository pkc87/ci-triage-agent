"""Precision, recall, confusion matrix and threshold sweep.

Hand-rolled on purpose. The whole repo exists to make one number defensible,
and a number you cannot open up is not defensible. It is ~60 lines; a framework
would be more code to read, not less.

The one subtlety worth reading carefully: this agent is allowed to ABSTAIN.
Below its confidence threshold it escalates to a human instead of deciding.
So there are two different questions, and both are reported:

  1. When it decides, how good are the decisions?   -> precision/recall over
     decided cases only (selective prediction).
  2. How often does it decide at all?               -> abdeckung (coverage).

Reporting only (1) would let a 99%-precision agent that escalates 98% of cases
look excellent. Reporting only (2) hides whether the decisions were any good.
Both, always, side by side.
"""

from __future__ import annotations

from typing import Iterable, Sequence

KLASSEN = ("PRODUKTFEHLER", "KAPUTTER_TEST", "FLAKE")
ESKALIERT = "ESKALATION_MENSCH"


def konfusionsmatrix(paare: Iterable[tuple[str, str]],
                     klassen: Sequence[str] = KLASSEN) -> dict[str, dict[str, int]]:
    """rows = true label, cols = predicted label plus an escalation column."""
    spalten = list(klassen) + [ESKALIERT]
    matrix = {w: {p: 0 for p in spalten} for w in klassen}
    for wahr, vorhergesagt in paare:
        if wahr not in matrix:
            raise ValueError(f"unknown true label: {wahr}")
        if vorhergesagt not in spalten:
            raise ValueError(f"unknown prediction: {vorhergesagt}")
        matrix[wahr][vorhergesagt] += 1
    return matrix


def _prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1


def kennzahlen(paare: Sequence[tuple[str, str]],
               klassen: Sequence[str] = KLASSEN) -> dict:
    """Per-class precision/recall/F1 over DECIDED cases, plus macro and coverage.

    Escalated cases are excluded from precision and recall -- the agent made no
    claim about them -- but they are counted in `abdeckung` and they still show
    up in the confusion matrix's escalation column, so nothing is hidden.
    """
    paare = list(paare)
    gesamt = len(paare)
    entschieden = [(w, v) for w, v in paare if v != ESKALIERT]
    matrix = konfusionsmatrix(paare, klassen)

    je_klasse: dict[str, dict] = {}
    for k in klassen:
        tp = sum(1 for w, v in entschieden if w == k and v == k)
        fp = sum(1 for w, v in entschieden if w != k and v == k)
        fn = sum(1 for w, v in entschieden if w == k and v != k)
        precision, recall, f1 = _prf(tp, fp, fn)
        je_klasse[k] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support_gesamt": sum(1 for w, _ in paare if w == k),
            "support_entschieden": sum(1 for w, _ in entschieden if w == k),
            "eskaliert": matrix[k][ESKALIERT],
            "tp": tp, "fp": fp, "fn": fn,
        }

    # Macro-average over classes that actually got decided. A class the agent
    # escalated entirely contributes no score -- averaging in a 0.0 for it would
    # punish abstention, which is the behaviour we are trying to reward.
    bewertbar = [k for k in klassen if je_klasse[k]["support_entschieden"] > 0]
    def _macro(feld: str) -> float:
        if not bewertbar:
            return 0.0
        return round(sum(je_klasse[k][feld] for k in bewertbar) / len(bewertbar), 4)

    return {
        "faelle_gesamt": gesamt,
        "faelle_entschieden": len(entschieden),
        "faelle_eskaliert": gesamt - len(entschieden),
        "abdeckung": round(len(entschieden) / gesamt, 4) if gesamt else 0.0,
        "eskalationsquote": round((gesamt - len(entschieden)) / gesamt, 4) if gesamt else 0.0,
        "genauigkeit_entschieden": round(
            sum(1 for w, v in entschieden if w == v) / len(entschieden), 4
        ) if entschieden else 0.0,
        "macro_precision": _macro("precision"),
        "macro_recall": _macro("recall"),
        "macro_f1": _macro("f1"),
        "macro_basis": bewertbar,
        "je_klasse": je_klasse,
        "konfusion": matrix,
    }


def versenkte_produktfehler(paare_mit_aktion: Iterable[tuple[str, str]]) -> int:
    """Count real product bugs that were silently auto-rerun away.

    The metric this project actually cares about. A product bug that gets a
    wrong TICKET wastes an hour. A product bug that gets RERUN disappears from
    the board and ships. These are not equally bad, so they are not averaged
    into one score -- this one is counted on its own.
    """
    return sum(1 for wahr, aktion in paare_mit_aktion
               if wahr == "PRODUKTFEHLER" and aktion == "RERUN")
