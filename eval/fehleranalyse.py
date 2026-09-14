"""Group the agent's mistakes so the pattern is visible, not the anecdotes.

A list of fifty individual wrong answers tells you nothing. The same list
grouped by (truth -> prediction) and sorted by confidence tells you what the
agent systematically believes that is not true, which is the only kind of error
worth writing down.

  python eval/fehleranalyse.py
  python eval/fehleranalyse.py --schwelle 0.85 --alle
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))

from agent.schema import entscheide, FLAKE_AUFSCHLAG  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--vorhersagen", default=str(HIER / "predictions_cli.jsonl"))
    p.add_argument("--schwelle", type=float, default=0.70)
    p.add_argument("--alle", action="store_true",
                   help="also list correct verdicts and escalations")
    p.add_argument("--breite", type=int, default=230, help="chars of rationale to show")
    args = p.parse_args()

    pfad = Path(args.vorhersagen)
    if not pfad.exists():
        raise SystemExit(f"{pfad} does not exist -- run the eval first")
    zeilen = [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]

    gruppen: dict[tuple[str, str], list[dict]] = defaultdict(list)
    eskaliert: list[dict] = []
    richtig = 0

    for v in zeilen:
        wahr = v["label"]
        if v["klasse"] is None:
            eskaliert.append({**v, "warum": "unparseable verdict"})
            continue
        aktion = entscheide(v["klasse"], v["konfidenz"], args.schwelle, FLAKE_AUFSCHLAG)
        if aktion == "ESKALATION_MENSCH":
            eskaliert.append({**v, "warum": f"confidence {v['konfidenz']:.2f} below bar"})
            continue
        if v["klasse"] == wahr:
            richtig += 1
            continue
        gruppen[(wahr, v["klasse"])].append(v)

    gesamt = len(zeilen)
    falsch = sum(len(g) for g in gruppen.values())
    print(f"{gesamt} cases at threshold {args.schwelle}: "
          f"{richtig} right, {falsch} wrong, {len(eskaliert)} escalated\n")

    if not gruppen:
        print("no misclassifications at this threshold")
    for (wahr, vorhergesagt), faelle in sorted(gruppen.items(), key=lambda kv: -len(kv[1])):
        print(f"=== {wahr}  ->  {vorhergesagt}   ({len(faelle)} case(s))")
        for v in sorted(faelle, key=lambda z: -z["konfidenz"]):
            print(f"  {v['fall_id']:<12} konf {v['konfidenz']:.2f}  [{v.get('quelle', '?')}]")
            print(f"      {v['begruendung'][:args.breite]}")
            if v.get("beleg"):
                print(f"      beleg: {v['beleg'][:140].replace(chr(10), ' ')}")
        print()

    # The dangerous ones, called out separately: a product bug sent to RERUN
    # vanishes. Nothing else in this report is in the same cost class.
    versenkt = [v for v in zeilen
                if v["label"] == "PRODUKTFEHLER" and v["klasse"] is not None
                and entscheide(v["klasse"], v["konfidenz"], args.schwelle,
                               FLAKE_AUFSCHLAG) == "RERUN"]
    print(f"=== BURIED PRODUCT BUGS (auto-rerun, would never reach a human): {len(versenkt)}")
    for v in versenkt:
        print(f"  {v['fall_id']:<12} konf {v['konfidenz']:.2f}  {v['begruendung'][:args.breite]}")
    print()

    if args.alle:
        print(f"=== ESCALATED ({len(eskaliert)})")
        for v in sorted(eskaliert, key=lambda z: z.get("konfidenz") or 0):
            k = v["konfidenz"]
            kk = f"{k:.2f}" if k is not None else " -- "
            richtig_gewesen = "would have been right" if v["klasse"] == v["label"] else \
                              f"would have said {v['klasse']}"
            print(f"  {v['fall_id']:<12} konf {kk}  truth {v['label']:<14} "
                  f"{richtig_gewesen}  ({v['warum']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
