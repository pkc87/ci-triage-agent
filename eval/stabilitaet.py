"""How much of the headline number is the agent, and how much is the dice?

A single eval run reports one number. Run the same corpus through the same
model twice and the number moves, because sampling is not deterministic. If it
moves by more than the difference you are claiming between two prompts, the
claim is noise.

This compares two prediction files over the same corpus and reports:

  * class agreement -- how often the two runs picked the same class
  * mean absolute confidence drift -- how much the number the threshold acts on
    wobbles between runs
  * action agreement at the operating threshold -- the only one that changes
    what a team actually experiences

  python eval/run_eval.py --backend cli --vorhersagen eval/predictions_lauf1.jsonl
  python eval/run_eval.py --backend cli --vorhersagen eval/predictions_lauf2.jsonl
  python eval/stabilitaet.py eval/predictions_lauf1.jsonl eval/predictions_lauf2.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))

from agent.schema import FLAKE_AUFSCHLAG, entscheide  # noqa: E402


def lies(pfad: Path) -> dict[str, dict]:
    if not pfad.exists():
        raise SystemExit(f"{pfad} does not exist")
    return {z["fall_id"]: z for z in
            (json.loads(l) for l in pfad.read_text(encoding="utf-8").splitlines() if l.strip())}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("lauf_a")
    p.add_argument("lauf_b")
    p.add_argument("--schwelle", type=float, default=0.70)
    p.add_argument("--ausgabe", default=str(HIER / "stabilitaet.json"))
    args = p.parse_args()

    a, b = lies(Path(args.lauf_a)), lies(Path(args.lauf_b))
    gemeinsam = sorted(set(a) & set(b))
    if not gemeinsam:
        raise SystemExit("the two runs share no cases")

    gleiche_klasse = 0
    drift_summe = 0.0
    gleiche_aktion = 0
    abweichler: list[dict] = []
    # A run that errored out produced no verdict at all. Counting that as the
    # model "changing its mind" would blame nondeterminism for a broken pipe --
    # so failures are excluded from the agreement rates and reported on their
    # own line. They are a real problem, just a different one.
    ausgefallen: list[dict] = []
    beantwortet = 0

    for fid in gemeinsam:
        va, vb = a[fid], b[fid]
        ka, kb = va["klasse"], vb["klasse"]
        if ka is None or kb is None:
            ausgefallen.append({
                "fall_id": fid,
                "lauf": "A" if ka is None else ("B" if kb is None else "beide"),
                "fehler": (va.get("fehler") or vb.get("fehler") or "")[:200],
            })
            continue
        beantwortet += 1
        if ka == kb:
            gleiche_klasse += 1
        drift_summe += abs(va["konfidenz"] - vb["konfidenz"])
        aa = entscheide(ka, va["konfidenz"], args.schwelle, FLAKE_AUFSCHLAG)
        ab = entscheide(kb, vb["konfidenz"], args.schwelle, FLAKE_AUFSCHLAG)
        if aa == ab:
            gleiche_aktion += 1
        else:
            abweichler.append({"fall_id": fid, "label": va.get("label"),
                               "a": f"{ka} {va['konfidenz']:.2f} -> {aa}",
                               "b": f"{kb} {vb['konfidenz']:.2f} -> {ab}"})

    n = len(gemeinsam)
    teiler = beantwortet or 1
    bericht = {
        "faelle": n,
        "von_beiden_beantwortet": beantwortet,
        "ausgefallen": ausgefallen,
        "klassen_uebereinstimmung": round(gleiche_klasse / teiler, 4),
        "mittlere_konfidenz_drift": round(drift_summe / teiler, 4),
        "aktions_uebereinstimmung": round(gleiche_aktion / teiler, 4),
        "schwelle": args.schwelle,
        "abweichler": abweichler,
    }
    Path(args.ausgabe).write_text(json.dumps(bericht, ensure_ascii=False, indent=2) + "\n",
                                  encoding="utf-8")

    print(f"{n} cases in both runs; {beantwortet} answered by both")
    if ausgefallen:
        print(f"  {len(ausgefallen)} excluded -- one run produced no verdict "
              f"(backend/parse failure, not a change of mind):")
        for w in ausgefallen:
            print(f"    {w['fall_id']:<12} failed in run {w['lauf']}: {w['fehler'][:90]}")
    print(f"  same class:          {bericht['klassen_uebereinstimmung']:.0%}")
    print(f"  same action @ {args.schwelle}:  {bericht['aktions_uebereinstimmung']:.0%}")
    print(f"  mean |confidence a - b|: {bericht['mittlere_konfidenz_drift']:.3f}")
    if abweichler:
        print(f"\n  {len(abweichler)} case(s) where the two runs would act differently:")
        for w in abweichler:
            print(f"    {w['fall_id']:<12} truth {str(w['label']):<14} A: {w['a']:<34} B: {w['b']}")
    print(f"\nwrote {args.ausgabe}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
