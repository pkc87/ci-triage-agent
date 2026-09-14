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

import math
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
            "precision_ci95": wilson(tp, tp + fp),
            "recall": round(recall, 4),
            "recall_ci95": wilson(tp, tp + fn),
            "f1": round(f1, 4),
            "support_gesamt": sum(1 for w, _ in paare if w == k),
            "support_entschieden": sum(1 for w, _ in entschieden if w == k),
            "eskaliert": matrix[k][ESKALIERT],
            "tp": tp, "fp": fp, "fn": fn,
        }

    # Macro averages, over the classes for which the quantity is actually
    # defined -- and precision and recall are defined over different sets.
    #
    # Precision asks "when it said X, was it X?", so it needs the agent to have
    # said X at least once: tp+fp > 0. A class it never predicts has undefined
    # precision, not zero. Scoring it zero was the old behaviour here and it
    # produced a genuinely misleading artefact: raising the threshold past the
    # point where the agent stopped predicting FLAKE dropped macro precision
    # from 0.87 to 0.55, which reads as the agent getting worse when what
    # actually happened is that it got more cautious.
    #
    # Recall asks "of the real X, how many did it catch?", so it needs decided
    # cases of X to exist: tp+fn > 0.
    basis_precision = [k for k in klassen if je_klasse[k]["tp"] + je_klasse[k]["fp"] > 0]
    basis_recall = [k for k in klassen if je_klasse[k]["tp"] + je_klasse[k]["fn"] > 0]

    def _macro(feld: str, basis: list[str]) -> float:
        if not basis:
            return 0.0
        return round(sum(je_klasse[k][feld] for k in basis) / len(basis), 4)

    for k in klassen:
        if k not in basis_precision:
            je_klasse[k]["precision"] = None
            je_klasse[k]["precision_ci95"] = None
        if k not in basis_recall:
            je_klasse[k]["recall"] = None
            je_klasse[k]["recall_ci95"] = None
        if je_klasse[k]["precision"] is None or je_klasse[k]["recall"] is None:
            je_klasse[k]["f1"] = None

    bewertbar = [k for k in klassen if je_klasse[k]["support_entschieden"] > 0]

    return {
        "faelle_gesamt": gesamt,
        "faelle_entschieden": len(entschieden),
        "faelle_eskaliert": gesamt - len(entschieden),
        "abdeckung": round(len(entschieden) / gesamt, 4) if gesamt else 0.0,
        "eskalationsquote": round((gesamt - len(entschieden)) / gesamt, 4) if gesamt else 0.0,
        "genauigkeit_entschieden": round(
            sum(1 for w, v in entschieden if w == v) / len(entschieden), 4
        ) if entschieden else 0.0,
        "macro_precision": _macro("precision", basis_precision),
        "macro_recall": _macro("recall", basis_recall),
        "macro_f1": round(
            sum(je_klasse[k]["f1"] for k in klassen if je_klasse[k]["f1"] is not None)
            / len([k for k in klassen if je_klasse[k]["f1"] is not None]), 4
        ) if any(je_klasse[k]["f1"] is not None for k in klassen) else 0.0,
        "macro_basis": bewertbar,
        "macro_basis_precision": basis_precision,
        "macro_basis_recall": basis_recall,
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


def wilson(treffer: int, versuche: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a proportion.

    Present because of the honest answer to "how good is it really": with a
    corpus this size, a per-class recall of 0.80 over 15 cases is compatible
    with anything from roughly 0.55 to 0.93. Reporting the point estimate alone
    would be the most misleading thing in this repo -- more misleading than a
    low score, because it looks precise.

    Wilson rather than the normal approximation: it does not produce intervals
    that run below 0 or above 1, and it stays sane at small n and at p near the
    edges, which is exactly the regime this corpus lives in.
    """
    if versuche == 0:
        return (0.0, 0.0)
    p = treffer / versuche
    nenner = 1 + z * z / versuche
    mitte = (p + z * z / (2 * versuche)) / nenner
    spanne = z * math.sqrt(p * (1 - p) / versuche + z * z / (4 * versuche * versuche)) / nenner
    return (round(max(0.0, mitte - spanne), 4), round(min(1.0, mitte + spanne), 4))


def kalibrierung(paare: Sequence[tuple[float, bool]],
                 kanten: Sequence[float] = (0.0, 0.6, 0.75, 0.9, 1.01)) -> list[dict]:
    """Does a stated confidence mean anything?

    The whole design rests on one assumption: that the number the model reports
    tracks how often it is actually right. If it does not, the threshold is
    theatre -- it would be sorting by a quantity unrelated to correctness, and
    every sweep row would be meaningless.

    So this bins predictions by stated confidence and reports the observed hit
    rate in each bin. A calibrated agent produces a rising column. Published
    next to the headline numbers, because a reader is entitled to check the
    assumption rather than take it.
    """
    ausgabe = []
    for unten, oben in zip(kanten, kanten[1:]):
        drin = [(k, ok) for k, ok in paare if unten <= k < oben]
        if not drin:
            ausgabe.append({"von": unten, "bis": min(oben, 1.0), "n": 0,
                            "richtig": 0, "trefferquote": None,
                            "mittlere_konfidenz": None, "ci95": (0.0, 0.0)})
            continue
        richtig = sum(1 for _, ok in drin if ok)
        ausgabe.append({
            "von": unten,
            "bis": min(oben, 1.0),
            "n": len(drin),
            "richtig": richtig,
            "trefferquote": round(richtig / len(drin), 4),
            "mittlere_konfidenz": round(sum(k for k, _ in drin) / len(drin), 4),
            "ci95": wilson(richtig, len(drin)),
        })
    return ausgabe
