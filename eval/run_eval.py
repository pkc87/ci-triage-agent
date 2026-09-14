"""Run the agent over the whole corpus, score it, sweep the threshold.

Two phases, deliberately separated:

  INFERENCE  one model call per case -> predictions.jsonl (class + confidence)
  SCORING    pure arithmetic over that file -> ergebnis.json

The threshold never enters the inference phase. That is why a 10-row sweep
costs one model call per case instead of ten, and why every row of the sweep is
computed from exactly the same model output -- so differences between rows are
the policy changing, never the model drifting.

  python eval/run_eval.py                     # infer + score
  python eval/run_eval.py --nur-auswerten     # re-score stored predictions
  python eval/run_eval.py --backend stub      # no model, no spend (CI)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))

from agent.backends import baue_backend                        # noqa: E402
from agent.evidence import lade_fall                           # noqa: E402
from agent.schema import FLAKE_AUFSCHLAG, KLASSEN, entscheide  # noqa: E402
from agent.triage import triagiere                             # noqa: E402
from eval.metrics import (ESKALIERT, kalibrierung, kennzahlen,  # noqa: E402
                          versenkte_produktfehler)

SCHWELLEN = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95]

# The operating point this system ships with. The reasoning is in the README
# under "Where the threshold sits"; the number lives here so the code and the
# prose cannot drift apart.
BETRIEBSSCHWELLE = 0.70


def lade_ground_truth(pfad: Path) -> list[dict]:
    faelle = []
    for nr, zeile in enumerate(pfad.read_text(encoding="utf-8").splitlines(), 1):
        zeile = zeile.strip()
        if not zeile or zeile.startswith("//"):
            continue
        try:
            eintrag = json.loads(zeile)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{pfad}:{nr}: invalid JSON: {exc}")
        for feld in ("id", "label", "quelle", "gelabelt_von"):
            if feld not in eintrag:
                raise SystemExit(f"{pfad}:{nr}: missing field {feld!r}")
        if eintrag["label"] not in KLASSEN:
            raise SystemExit(f"{pfad}:{nr}: unknown label {eintrag['label']!r}")
        faelle.append(eintrag)
    ids = [f["id"] for f in faelle]
    if len(ids) != len(set(ids)):
        doppelt = {i for i in ids if ids.count(i) > 1}
        raise SystemExit(f"duplicate ids in ground truth: {sorted(doppelt)}")
    return faelle


def inferiere(faelle: list[dict], fall_wurzel: Path, backend_name: str,
              modell: str | None, mit_screenshot: bool, parallel: int) -> list[dict]:
    backend = baue_backend(backend_name, modell)
    gesamt = len(faelle)

    def einer(eintrag: dict) -> dict:
        pfad = fall_wurzel / eintrag["id"]
        ergebnis = triagiere(
            lade_fall(pfad), backend,
            # The inference-time threshold is irrelevant: scoring re-derives
            # every action from the stored confidence. The operating point is
            # passed so that raw output of this file agrees with the single-case
            # CLI if anyone reads it directly.
            schwelle=BETRIEBSSCHWELLE, mit_screenshot=mit_screenshot,
        )
        zeile = ergebnis.as_dict()
        zeile["label"] = eintrag["label"]
        zeile["quelle"] = eintrag["quelle"]
        return zeile

    start = time.monotonic()
    vorhersagen = []
    with ThreadPoolExecutor(max_workers=parallel) as pool:
        for i, zeile in enumerate(pool.map(einer, faelle), 1):
            vorhersagen.append(zeile)
            marke = "!" if zeile["klasse"] is None else " "
            print(f"  [{i:>3}/{gesamt}] {marke} {zeile['fall_id']:<12} "
                  f"{str(zeile['klasse']):<14} {zeile['konfidenz']}", flush=True)
    print(f"  inference took {time.monotonic() - start:.0f}s")
    # Keep corpus order rather than completion order, so that diffs between two
    # runs of this file are readable.
    nach_id = {z["fall_id"]: z for z in vorhersagen}
    return [nach_id[f["id"]] for f in faelle]


def werte_aus(vorhersagen: list[dict], schwelle: float,
              flake_aufschlag: float = FLAKE_AUFSCHLAG) -> dict:
    paare, paare_aktion = [], []
    for v in vorhersagen:
        if v["klasse"] is None:        # unparseable verdict -> handed to a human
            aktion = ESKALIERT
            vorhergesagt = ESKALIERT
        else:
            aktion = entscheide(v["klasse"], v["konfidenz"], schwelle, flake_aufschlag)
            vorhergesagt = ESKALIERT if aktion == ESKALIERT else v["klasse"]
        paare.append((v["label"], vorhergesagt))
        paare_aktion.append((v["label"], aktion))

    ergebnis = kennzahlen(paare)
    ergebnis["schwelle"] = schwelle
    ergebnis["flake_aufschlag"] = flake_aufschlag
    ergebnis["versenkte_produktfehler"] = versenkte_produktfehler(paare_aktion)
    ergebnis["parse_fehler"] = sum(1 for v in vorhersagen if v["klasse"] is None)
    return ergebnis


def sweep(vorhersagen: list[dict]) -> list[dict]:
    zeilen = []
    for s in SCHWELLEN:
        k = werte_aus(vorhersagen, s)
        zeilen.append({
            "schwelle": s,
            "macro_precision": k["macro_precision"],
            "macro_recall": k["macro_recall"],
            "macro_f1": k["macro_f1"],
            "abdeckung": k["abdeckung"],
            "eskalationsquote": k["eskalationsquote"],
            "genauigkeit_entschieden": k["genauigkeit_entschieden"],
            "versenkte_produktfehler": k["versenkte_produktfehler"],
            "produktfehler_recall": k["je_klasse"]["PRODUKTFEHLER"]["recall"],
            # How many classes the macro actually averaged. Once a class is
            # fully escalated it drops out of the basis, and the macro stops
            # being comparable to the rows above it -- which looks like a jump
            # in quality and is not one.
            "macro_basis": k["macro_basis"],
            "macro_basis_precision": k["macro_basis_precision"],
            "macro_basis_recall": k["macro_basis_recall"],
        })
    return zeilen


def herkunft(faelle: list[dict]) -> dict:
    def zaehl(schluessel: str) -> dict[str, int]:
        aus: dict[str, int] = {}
        for f in faelle:
            aus[f[schluessel]] = aus.get(f[schluessel], 0) + 1
        return dict(sorted(aus.items()))
    return {
        "gesamt": len(faelle),
        "nach_quelle": zaehl("quelle"),
        "nach_label": zaehl("label"),
        "nach_labelquelle": zaehl("gelabelt_von"),
    }


def _z(wert) -> str:
    """None means undefined, not zero -- see eval/metrics.py:kennzahlen."""
    return "  -  " if wert is None else f"{wert:.2f}"


def als_markdown(ergebnis: dict) -> str:
    z = []
    b = ergebnis["betriebspunkt"]
    quellen = ", ".join(f"{v} {k}" for k, v in ergebnis["herkunft"]["nach_quelle"].items())
    z.append(f"Cases: **{ergebnis['herkunft']['gesamt']}** ({quellen})  ")
    z.append(f"Backend: `{ergebnis['backend']}` - model `{ergebnis['modell']}` - "
             f"threshold **{b['schwelle']}** (FLAKE needs +{b['flake_aufschlag']})")
    z.append("")
    z.append("| Class | Precision | Recall | F1 | Cases | Decided | Escalated |")
    z.append("|---|---|---|---|---|---|---|")
    for k in KLASSEN:
        j = b["je_klasse"][k]
        z.append(f"| {k} | {_z(j['precision'])} | {_z(j['recall'])} | {_z(j['f1'])} | "
                 f"{j['support_gesamt']} | {j['support_entschieden']} | {j['eskaliert']} |")
    z.append(f"| **macro** | **{b['macro_precision']:.2f}** | **{b['macro_recall']:.2f}** | "
             f"**{b['macro_f1']:.2f}** | {b['faelle_gesamt']} | {b['faelle_entschieden']} | "
             f"{b['faelle_eskaliert']} |")
    z.append("")
    z.append(f"Coverage {b['abdeckung']:.0%} - accuracy on decided cases "
             f"{b['genauigkeit_entschieden']:.0%} - "
             f"**product bugs silently auto-rerun: {b['versenkte_produktfehler']}**")
    z.append("")
    z.append("**Confusion matrix** (rows = truth, columns = what the agent did)")
    z.append("")
    z.append("| truth \\ predicted | PRODUKTFEHLER | KAPUTTER_TEST | FLAKE | escalated |")
    z.append("|---|---|---|---|---|")
    for k in KLASSEN:
        r = b["konfusion"][k]
        z.append(f"| **{k}** | {r['PRODUKTFEHLER']} | {r['KAPUTTER_TEST']} | "
                 f"{r['FLAKE']} | {r[ESKALIERT]} |")
    z.append("")
    z.append("**Threshold sweep**")
    z.append("")
    z.append("| threshold | macro P | macro R | classes averaged | PRODUKTFEHLER recall | coverage | escalated | buried bugs |")
    z.append("|---|---|---|---|---|---|---|---|")
    for r in ergebnis["sweep"]:
        stern = " <-" if r["schwelle"] == b["schwelle"] else ""
        n_basis = len(r.get("macro_basis_precision", KLASSEN))
        basis = f"{n_basis}/3" + ("" if n_basis == 3 else " !")
        pf = r["produktfehler_recall"]
        z.append(f"| {r['schwelle']:.2f}{stern} | {r['macro_precision']:.2f} | "
                 f"{r['macro_recall']:.2f} | {basis} | {_z(pf)} | "
                 f"{r['abdeckung']:.0%} | {r['eskalationsquote']:.0%} | "
                 f"{r['versenkte_produktfehler']} |")
    return "\n".join(z)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Score the triage agent against the corpus.")
    p.add_argument("--backend", default="cli", choices=("api", "cli", "stub"))
    p.add_argument("--modell", default=None)
    p.add_argument("--schwelle", type=float, default=BETRIEBSSCHWELLE)
    p.add_argument("--mit-screenshot", action="store_true")
    p.add_argument("--parallel", type=int, default=6)
    p.add_argument("--nur-auswerten", action="store_true",
                   help="re-score stored predictions without calling a model")
    p.add_argument("--vorhersagen", default=None, help="predictions file to read/write")
    p.add_argument("--ausgabe", default=None, help="result file to write")
    p.add_argument("--ground-truth", default=str(HIER / "ground_truth.jsonl"))
    args = p.parse_args(argv)

    suffix = "_screenshot" if args.mit_screenshot else ""
    vorhersage_pfad = Path(args.vorhersagen
                           or HIER / f"predictions_{args.backend}{suffix}.jsonl")
    ausgabe_pfad = Path(args.ausgabe or HIER / "ergebnis.json")

    faelle = lade_ground_truth(Path(args.ground_truth))
    print(f"corpus: {len(faelle)} cases from {args.ground_truth}")

    if args.nur_auswerten:
        if not vorhersage_pfad.exists():
            raise SystemExit(f"{vorhersage_pfad} does not exist -- "
                             "run once without --nur-auswerten first")
        vorhersagen = [json.loads(z) for z in
                       vorhersage_pfad.read_text(encoding="utf-8").splitlines() if z.strip()]
        bekannt = {f["id"]: f for f in faelle}
        vorhanden = {v["fall_id"] for v in vorhersagen}
        fehlend = [f["id"] for f in faelle if f["id"] not in vorhanden]
        if fehlend:
            raise SystemExit(f"stored predictions are missing {len(fehlend)} "
                             f"cases: {fehlend[:5]}")
        for v in vorhersagen:            # refresh labels in case they were corrected
            v["label"] = bekannt[v["fall_id"]]["label"]
            v["quelle"] = bekannt[v["fall_id"]]["quelle"]
        print(f"scoring stored predictions from {vorhersage_pfad.name}")
    else:
        vorhersagen = inferiere(faelle, HIER / "cases", args.backend, args.modell,
                                args.mit_screenshot, args.parallel)
        vorhersage_pfad.write_text(
            "\n".join(json.dumps(v, ensure_ascii=False) for v in vorhersagen) + "\n",
            encoding="utf-8")

    modell = args.modell or ("keyword-rules" if args.backend == "stub" else "claude-sonnet-5")
    ergebnis = {
        "erzeugt_am": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "backend": args.backend,
        "modell": modell,
        "mit_screenshot": args.mit_screenshot,
        "herkunft": herkunft(faelle),
        "betriebspunkt": werte_aus(vorhersagen, args.schwelle),
        "sweep": sweep(vorhersagen),
        "ablation_ohne_flake_aufschlag": werte_aus(vorhersagen, args.schwelle,
                                                   flake_aufschlag=0.0),
        # Independent of any threshold: does the stated confidence track being
        # right? If this column does not rise, the threshold sorts by noise.
        "kalibrierung": kalibrierung([(v["konfidenz"], v["klasse"] == v["label"])
                                      for v in vorhersagen if v["klasse"] is not None]),
    }
    ausgabe_pfad.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
    tabelle = als_markdown(ergebnis)
    (ausgabe_pfad.parent / f"{ausgabe_pfad.stem}.md").write_text(tabelle + "\n",
                                                                 encoding="utf-8")
    print()
    print(tabelle)
    print()
    print(f"wrote {ausgabe_pfad.name} and {ausgabe_pfad.stem}.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
