"""Corpus integrity check. Runs in CI on every pull request.

A ground-truth corpus rots quietly: a case gets renamed, an artefact referenced
in fall.json disappears, a label is edited to a typo, someone adds a case and
forgets the ground-truth line. None of that fails a test suite. All of it
silently changes the published numbers.

This file fails loudly instead.

  python eval/pruefe_korpus.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))

from agent.schema import KLASSEN  # noqa: E402

ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
PFLICHT = ("id", "quelle", "test_titel", "fehlermeldung")
QUELLEN = ("historisch", "synthetisch")


def main() -> int:
    gt_pfad = HIER / "ground_truth.jsonl"
    fall_wurzel = HIER / "cases"
    fehler: list[str] = []

    if not gt_pfad.exists():
        print(f"FEHLT: {gt_pfad}")
        return 1

    eintraege = []
    for nr, zeile in enumerate(gt_pfad.read_text(encoding="utf-8").splitlines(), 1):
        zeile = zeile.strip()
        if not zeile or zeile.startswith("//"):
            continue
        try:
            eintraege.append((nr, json.loads(zeile)))
        except json.JSONDecodeError as exc:
            fehler.append(f"ground_truth.jsonl:{nr}: invalid JSON: {exc}")

    gesehen: set[str] = set()
    for nr, e in eintraege:
        for feld in ("id", "label", "quelle", "gelabelt_von", "begruendung_label"):
            if feld not in e:
                fehler.append(f"ground_truth.jsonl:{nr}: missing {feld!r}")
        fall_id = e.get("id", "?")
        if fall_id in gesehen:
            fehler.append(f"ground_truth.jsonl:{nr}: duplicate id {fall_id!r}")
        gesehen.add(fall_id)
        if e.get("label") not in KLASSEN:
            fehler.append(f"ground_truth.jsonl:{nr}: bad label {e.get('label')!r}")
        if e.get("quelle") not in QUELLEN:
            fehler.append(f"ground_truth.jsonl:{nr}: bad quelle {e.get('quelle')!r}")

        d = fall_wurzel / fall_id
        if not d.is_dir():
            fehler.append(f"ground_truth.jsonl:{nr}: no case directory {d}")
            continue
        fj = d / "fall.json"
        if not fj.exists():
            fehler.append(f"{fall_id}: fall.json missing")
            continue
        try:
            fall = json.loads(fj.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            fehler.append(f"{fall_id}/fall.json: invalid JSON: {exc}")
            continue
        for feld in PFLICHT:
            if not fall.get(feld):
                fehler.append(f"{fall_id}/fall.json: empty or missing {feld!r}")
        if fall.get("id") != fall_id:
            fehler.append(f"{fall_id}/fall.json: id says {fall.get('id')!r}")
        if fall.get("quelle") != e.get("quelle"):
            fehler.append(f"{fall_id}: quelle disagrees between fall.json and ground truth")
        if ANSI.search(json.dumps(fall)):
            fehler.append(f"{fall_id}: ANSI escape codes left in the evidence")
        for name, datei in (fall.get("artefakte") or {}).items():
            if datei and not (d / datei).exists():
                fehler.append(f"{fall_id}: artefakte.{name} points at missing {datei!r}")
        # A case with no evidence beyond its title cannot be triaged by anyone.
        if len(str(fall.get("fehlermeldung", ""))) < 20:
            fehler.append(f"{fall_id}: error text is too short to be real evidence")

    for d in sorted(p for p in fall_wurzel.glob("*") if p.is_dir()):
        if d.name not in gesehen:
            fehler.append(f"{d.name}: case directory has no ground-truth line")

    print(f"cases in ground truth: {len(gesehen)}")
    verteilung: dict[str, int] = {}
    quellen: dict[str, int] = {}
    for _, e in eintraege:
        verteilung[e.get("label", "?")] = verteilung.get(e.get("label", "?"), 0) + 1
        quellen[e.get("quelle", "?")] = quellen.get(e.get("quelle", "?"), 0) + 1
    print(f"by label:  {verteilung}")
    print(f"by source: {quellen}")

    if fehler:
        print(f"\n{len(fehler)} problem(s):")
        for f in fehler:
            print(f"  - {f}")
        return 1
    print("\ncorpus OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
