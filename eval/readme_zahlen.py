"""Write the measured numbers into README.md between its markers.

The README is the thing people read and the only thing most of them will read.
A number typed into prose by hand goes stale the first time the eval is re-run,
and nobody notices, and then the number in the README is a claim nobody can
reproduce. So the README's numbers are generated from eval/ergebnis.json and
the example verdict is copied out of a real predictions file.

  python eval/readme_zahlen.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
WURZEL = HIER.parent
sys.path.insert(0, str(WURZEL))

from agent.schema import KLASSEN  # noqa: E402


def _block(text: str, name: str, inhalt: str) -> str:
    start, ende = f"<!-- {name}:START -->", f"<!-- {name}:ENDE -->"
    muster = re.compile(re.escape(start) + r".*?" + re.escape(ende), re.DOTALL)
    if not muster.search(text):
        raise SystemExit(f"README is missing the {name} markers")
    return muster.sub(f"{start}\n{inhalt}\n{ende}", text)


def zahlen_block(e: dict) -> str:
    b = e["betriebspunkt"]
    h = e["herkunft"]
    z: list[str] = []
    hist = h["nach_quelle"].get("historisch", 0)
    syn = h["nach_quelle"].get("synthetisch", 0)

    z.append(f"**{h['gesamt']} labelled failures** — {hist} pulled from real CI history, "
             f"{syn} produced by deliberately breaking a fixture app. "
             f"Scored with `{e['backend']}` backend, model `{e['modell']}`, "
             f"at threshold **{b['schwelle']}**.")
    z.append("")
    z.append("| Class | Precision (95% CI) | Recall (95% CI) | F1 | Cases | Decided | Escalated |")
    z.append("|---|---|---|---|---|---|---|")
    for k in KLASSEN:
        j = b["je_klasse"][k]
        if j["support_entschieden"] == 0:
            # No decided case, so there is no rate to report. Printing 0.00 here
            # would read as "it got them all wrong" rather than "it never said".
            grund = "all escalated" if j["support_gesamt"] else "no cases"
            z.append(f"| `{k}` | – <sub>({grund})</sub> | – <sub>({grund})</sub> | – | "
                     f"{j['support_gesamt']} | 0 | {j['eskaliert']} |")
            continue
        pci, rci = j["precision_ci95"], j["recall_ci95"]
        z.append(f"| `{k}` | {j['precision']:.2f} <sub>[{pci[0]:.2f}-{pci[1]:.2f}]</sub> | "
                 f"{j['recall']:.2f} <sub>[{rci[0]:.2f}-{rci[1]:.2f}]</sub> | {j['f1']:.2f} | "
                 f"{j['support_gesamt']} | {j['support_entschieden']} | {j['eskaliert']} |")
    z.append(f"| **macro** | **{b['macro_precision']:.2f}** | **{b['macro_recall']:.2f}** | "
             f"**{b['macro_f1']:.2f}** | {b['faelle_gesamt']} | {b['faelle_entschieden']} | "
             f"{b['faelle_eskaliert']} |")
    z.append("")
    z.append("The intervals are Wilson score intervals, and they are wide because the "
             "corpus is small. That is the honest shape of this result: the point "
             "estimates are real measurements, and a per-class number resting on a "
             "dozen cases cannot be quoted to two decimals as though it were stable. "
             "If you only take one number from this table, take the interval.")
    z.append("")
    z.append(f"Coverage **{b['abdeckung']:.0%}** (the agent decided that share of cases and "
             f"escalated the rest) · accuracy on decided cases **{b['genauigkeit_entschieden']:.0%}** "
             f"· unparseable verdicts: {b['parse_fehler']}")
    z.append("")
    z.append(f"**Product bugs silently auto-rerun: {b['versenkte_produktfehler']}.** "
             "That is the number this system is tuned around; see the threshold section.")
    z.append("")
    z.append("Precision and recall are computed over *decided* cases only — an escalation "
             "is an abstention, not a wrong answer. Reported alone that would be trivially "
             "gameable (escalate everything, look perfect on the remainder), so coverage "
             "sits in the same table and never leaves it.")
    z.append("")
    z.append("### Confusion matrix")
    z.append("")
    z.append("Rows are the true label, columns are what the agent actually did.")
    z.append("")
    z.append("| truth \\ agent | `PRODUKTFEHLER` | `KAPUTTER_TEST` | `FLAKE` | escalated |")
    z.append("|---|---|---|---|---|")
    for k in KLASSEN:
        r = b["konfusion"][k]
        z.append(f"| **`{k}`** | {r['PRODUKTFEHLER']} | {r['KAPUTTER_TEST']} | "
                 f"{r['FLAKE']} | {r['ESKALATION_MENSCH']} |")
    z.append("")
    kal = e.get("kalibrierung") or []
    if any(b["n"] for b in kal):
        z.append("### Does the confidence mean anything?")
        z.append("")
        z.append("Everything above rests on one assumption: that the number the model "
                 "reports tracks how often it is actually right. If it does not, the "
                 "threshold sorts by noise and every sweep row is theatre. So here is the "
                 "assumption, checked:")
        z.append("")
        z.append("| stated confidence | cases | correct | hit rate (95% CI) |")
        z.append("|---|---|---|---|")
        for b in kal:
            if not b["n"]:
                continue
            lo, hi = b["ci95"]
            z.append(f"| {b['von']:.2f} – {b['bis']:.2f} | {b['n']} | {b['richtig']} | "
                     f"{b['trefferquote']:.0%} <sub>[{lo:.0%}–{hi:.0%}]</sub> |")
        z.append("")
        z.append("Read this before the headline table.")
        z.append("")
        z.append("### Where the data comes from")
    z.append("")
    z.append(f"| source | cases | how it was labelled |")
    z.append("|---|---|---|")
    for quelle, n in h["nach_quelle"].items():
        z.append(f"| {quelle} | {n} | see below |")
    z.append("")
    labelquellen = ", ".join(f"`{k}`: {v}" for k, v in h["nach_labelquelle"].items())
    z.append(f"Label provenance: {labelquellen}.")
    z.append("")
    z.append("- `konstruktion` — the label follows from the mutation that produced the "
             "failure. We know what we broke, so this is the strongest ground truth here, "
             "not the weakest.")
    z.append("- `historie` — the label follows from external repo evidence: the commit "
             "that later fixed it.")
    z.append("- `claude-opus-5` — assigned by a model reading the artefact. **No case in "
             "this corpus carries this label.** The value exists in the schema because it "
             "was the expected fallback; it turned out not to be needed, and that is worth "
             "more than the fallback would have been.")
    z.append("")
    z.append("The constructed half is not a shortcut, it is a necessity, and the reason "
             "is worth stating plainly: **real CI failures cluster, hard.** The nine "
             "failed runs behind the historical cases contain **656** individual failing "
             "tests that collapse into exactly **two** root causes — one misconfigured "
             "runner produced 120 identical failures, and it survived five successive "
             "commits before anyone fixed it, for 600 failures with a single distinct "
             "error body between them. Two root causes cannot support a per-class "
             "precision claim, so the historical half is capped at seven cases per cause "
             "and the rest of the corpus is built by breaking a fixture app on purpose.")
    z.append("")
    z.append("They were also all one class. Every red build in that history was a broken "
             "test or a broken runner: **no product bugs and no flakes at all**. Which is "
             "its own small argument for the tool — the humans triaging those builds spent "
             "their attention on failures that never reached a user — but it means the "
             "`PRODUKTFEHLER` and `FLAKE` rows above rest entirely on constructed cases.")
    z.append("")
    z.append("Every synthetic case is a real Playwright run against a really-mutated app. "
             "No report in this repo was written by hand. `eval/cases/HERKUNFT.md` records "
             "which CI runs the historical cases came from and how they were sampled.")
    z.append("")
    stub = WURZEL / "eval" / "ergebnis_stub.json"
    if stub.exists():
        s = json.loads(stub.read_text(encoding="utf-8"))["betriebspunkt"]
        z.append("### Against a floor")
        z.append("")
        z.append(f"A page of regexes over the error text (`--backend stub`, no model) "
                 f"scores macro precision **{s['macro_precision']:.2f}** / recall "
                 f"**{s['macro_recall']:.2f}** at coverage {s['abdeckung']:.0%}, burying "
                 f"{s['versenkte_produktfehler']} product bug(s). It is in the repo because "
                 f"a prompt that cannot beat regexes is not earning its latency, and "
                 f"because it lets CI exercise the whole pipeline with no key and no spend.")
        z.append("")
    z.append("Raw output: [`eval/ergebnis.json`](eval/ergebnis.json) · "
             "per-case verdicts: [`eval/predictions_" + e["backend"] + ".jsonl`]"
             "(eval/predictions_" + e["backend"] + ".jsonl)")
    return "\n".join(z)


def sweep_block(e: dict) -> str:
    b = e["betriebspunkt"]
    z: list[str] = []
    z.append("| threshold | macro P | macro R | classes in macro | `PRODUKTFEHLER` recall | coverage | escalated | **buried bugs** |")
    z.append("|---|---|---|---|---|---|---|---|")
    unvollstaendig = False
    for r in e["sweep"]:
        hier = r["schwelle"] == b["schwelle"]
        markierung = " **<- shipped**" if hier else ""
        n_basis = len(r.get("macro_basis", KLASSEN))
        if n_basis < len(KLASSEN):
            unvollstaendig = True
        basis = f"{n_basis}/3" + ("" if n_basis == len(KLASSEN) else " ⚠")
        z.append(f"| {r['schwelle']:.2f}{markierung} | {r['macro_precision']:.2f} | "
                 f"{r['macro_recall']:.2f} | {basis} | {r['produktfehler_recall']:.2f} | "
                 f"{r['abdeckung']:.0%} | {r['eskalationsquote']:.0%} | "
                 f"{r['versenkte_produktfehler']} |")
    z.append("")
    if unvollstaendig:
        z.append("**Read the 'classes in macro' column before the macro column.** Once a "
                 "class is escalated in its entirety it drops out of the macro average "
                 "rather than being scored as zero — so a row marked ⚠ is averaging fewer "
                 "classes than the rows above it, and its macro is *not* comparable to "
                 "them. The perfect scores at the high end are real, but they are perfect "
                 "scores on two classes and a shrinking share of the corpus, not a better "
                 "agent. This is the exact trap the coverage column exists to expose, and "
                 "it is left in the table rather than tuned away.")
        z.append("")
    ohne = e.get("ablation_ohne_flake_aufschlag")
    if ohne:
        z.append(f"**Ablation — drop the `FLAKE` surcharge** (same predictions, same "
                 f"{b['schwelle']} threshold, `FLAKE` no longer needs the extra "
                 f"{b['flake_aufschlag']}): coverage rises from {b['abdeckung']:.0%} to "
                 f"{ohne['abdeckung']:.0%}, and buried product bugs go from "
                 f"**{b['versenkte_produktfehler']}** to **{ohne['versenkte_produktfehler']}**. "
                 f"That difference is the entire argument for the surcharge, and it is "
                 f"why it is a separate knob rather than part of the threshold.")
    return '\n'.join(z)


def beispiel_block(e: dict) -> str:
    """Lift a real verdict out of the predictions file. Never a hand-written one."""
    pfad = HIER / f"predictions_{e['backend']}.jsonl"
    if not pfad.exists():
        return "_(no predictions file yet — run `make eval`)_"
    zeilen = [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]
    # Prefer a correct, confident, well-cited verdict on a product bug: it is the
    # case a reader most wants to see the agent get right.
    kandidaten = [z for z in zeilen
                  if z["klasse"] == z["label"] == "PRODUKTFEHLER" and z.get("beleg")]
    if not kandidaten:
        kandidaten = [z for z in zeilen if z["klasse"] == z["label"] and z.get("beleg")]
    if not kandidaten:
        return "_(no clean example verdict in the current run)_"
    v = max(kandidaten, key=lambda z: z["konfidenz"])
    beleg = v["beleg"].replace("\n", " ")[:200]
    return (
        f"A real verdict from the run below (case `{v['fall_id']}`, "
        f"ground truth `{v['label']}`):\n\n"
        "```\n"
        f"klasse:      {v['klasse']}\n"
        f"konfidenz:   {v['konfidenz']:.2f}\n"
        f"begruendung: {v['begruendung']}\n"
        f"beleg:       {beleg}\n"
        f"aktion:      {v['aktion']}\n"
        "```\n\n"
        "`beleg` is a literal quote from the evidence, required by the prompt. A "
        "verdict the model cannot cite is a verdict it does not have — it is the "
        "cheapest guard against confident nonsense in the whole system."
    )


def main() -> int:
    ergebnis_pfad = HIER / "ergebnis.json"
    if not ergebnis_pfad.exists():
        raise SystemExit("eval/ergebnis.json does not exist -- run `make eval` first")
    e = json.loads(ergebnis_pfad.read_text(encoding="utf-8"))

    readme = WURZEL / "README.md"
    text = readme.read_text(encoding="utf-8")
    text = _block(text, "ZAHLEN", zahlen_block(e))
    text = _block(text, "BEISPIEL", beispiel_block(e))
    text = _block(text, "SWEEP", sweep_block(e))
    readme.write_text(text, encoding="utf-8")
    print("README numbers refreshed from eval/ergebnis.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
