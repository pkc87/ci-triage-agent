"""Merge the two corpus halves into the canonical ground truth.

The historical half is extracted from CI logs; the constructed half is emitted
by fixtures/generate.mjs. They are produced by different tools at different
times, so each writes its own file and this merges them. Deterministic order
(historical first, then constructed, each by id) so that a regenerated corpus
produces a readable diff rather than a reshuffle.

Refuses to write a corpus it would not want to publish: duplicate ids, a case
directory with no label, a label with no case directory.

  python eval/baue_ground_truth.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))

from agent.schema import KLASSEN  # noqa: E402

HAELFTEN = [HIER / "ground_truth_hist.jsonl", HIER / "ground_truth_syn.jsonl"]
ZIEL = HIER / "ground_truth.jsonl"


def main() -> int:
    eintraege: list[dict] = []
    for pfad in HAELFTEN:
        if not pfad.exists():
            print(f"  note: {pfad.name} not present, skipping")
            continue
        n = 0
        for zeile in pfad.read_text(encoding="utf-8").splitlines():
            if zeile.strip():
                eintraege.append(json.loads(zeile))
                n += 1
        print(f"  {pfad.name}: {n}")

    if not eintraege:
        raise SystemExit("no ground truth found -- nothing to merge")

    ids = [e["id"] for e in eintraege]
    doppelt = sorted({i for i in ids if ids.count(i) > 1})
    if doppelt:
        raise SystemExit(f"duplicate ids across the halves: {doppelt}")

    for e in eintraege:
        if e.get("label") not in KLASSEN:
            raise SystemExit(f"{e['id']}: bad label {e.get('label')!r}")
        if not (HIER / "cases" / e["id"]).is_dir():
            raise SystemExit(f"{e['id']}: labelled but no case directory")

    verzeichnisse = {d.name for d in (HIER / "cases").glob("*") if d.is_dir()}
    ohne_label = sorted(verzeichnisse - set(ids))
    if ohne_label:
        raise SystemExit(f"case directories with no ground-truth line: {ohne_label}")

    rang = {"historisch": 0, "synthetisch": 1}
    eintraege.sort(key=lambda e: (rang.get(e["quelle"], 9), e["id"]))
    ZIEL.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in eintraege) + "\n",
                    encoding="utf-8")

    verteilung: dict[str, int] = {}
    for e in eintraege:
        schluessel = f"{e['quelle']}/{e['label']}"
        verteilung[schluessel] = verteilung.get(schluessel, 0) + 1
    print(f"\nwrote {ZIEL.name}: {len(eintraege)} cases")
    for k in sorted(verteilung):
        print(f"  {k:<30} {verteilung[k]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
