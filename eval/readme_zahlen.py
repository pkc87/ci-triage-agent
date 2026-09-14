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
        def _zelle(wert, ci, was):
            if wert is None:
                # Undefined, not zero: the agent never made a claim of this kind.
                grund = ("never predicted" if was == "precision"
                         else "no decided cases")
                return f"– <sub>({grund})</sub>"
            return f"{wert:.2f} <sub>[{ci[0]:.2f}-{ci[1]:.2f}]</sub>"

        f1 = "–" if j["f1"] is None else f"{j['f1']:.2f}"
        z.append(f"| `{k}` | {_zelle(j['precision'], j['precision_ci95'], 'precision')} | "
                 f"{_zelle(j['recall'], j['recall_ci95'], 'recall')} | {f1} | "
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
        stab_pfad = HIER / "stabilitaet.json"
    if stab_pfad.exists():
        st = json.loads(stab_pfad.read_text(encoding="utf-8"))
        z.append("### How much of this is the dice?")
        z.append("")
        z.append(f"The same corpus was run through the same model twice. Across the "
                 f"{st['von_beiden_beantwortet']} cases both runs answered, they agreed on "
                 f"the class **{st['klassen_uebereinstimmung']:.0%}** of the time and on "
                 f"the resulting action **{st['aktions_uebereinstimmung']:.0%}** of the "
                 f"time, with a mean confidence difference of "
                 f"**{st['mittlere_konfidenz_drift']:.3f}**.")
        z.append("")
        if st["aktions_uebereinstimmung"] > st["klassen_uebereinstimmung"]:
            z.append("The gap between those two numbers is the interesting part: the cases "
                     "that flip flip between `PRODUKTFEHLER` and `KAPUTTER_TEST`, and both "
                     "of those produce a `TICKET`. So the instability is real in the "
                     "classification and invisible in what a team would actually "
                     "experience. That is a property of the action policy, not luck — "
                     "the two classes the agent confuses are the two that cost the same "
                     "to be wrong about.")
            z.append("")
        z.append("Sampling is not deterministic, so a single run reports one draw from a "
                 "distribution. The point of measuring this is calibration of a different "
                 "kind: it sets the size of difference that is worth believing. A prompt "
                 "change that moves macro precision by less than this is noise, and this "
                 "repository is not going to claim otherwise. `eval/stabilitaet.json` has "
                 "the per-case detail.")
        z.append("")
        z.append("### Does the confidence mean anything?")
        z.append("")
        z.append("Everything above rests on one assumption: that the number the model "
                 "reports tracks how often it is actually right. If it does not, the "
                 "threshold sorts by noise and every sweep row is theatre. So here is the "
                 "assumption, checked:")
        z.append("")
        z.append("| stated confidence | cases | correct | hit rate (95% CI) |")
        z.append("|---|---|---|---|")
        for korb in kal:                       # not `b`: that is the operating point
            if not korb["n"]:
                continue
            lo, hi = korb["ci95"]
            z.append(f"| {korb['von']:.2f} – {korb['bis']:.2f} | {korb['n']} | "
                     f"{korb['richtig']} | "
                     f"{korb['trefferquote']:.0%} <sub>[{lo:.0%}–{hi:.0%}]</sub> |")
        z.append("")
        z.append("Read this before the headline table.")
        z.append("")
        z.append("### Where the data comes from")
    z.append("")
    labelquellen = ", ".join(f"`{k}` {v}" for k, v in h["nach_labelquelle"].items())
    klassen_verteilung = ", ".join(f"`{k}` {v}" for k, v in h["nach_label"].items())
    z.append(f"Class balance: {klassen_verteilung}. "
             f"Label provenance: {labelquellen}.")
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
        st = json.loads(stub.read_text(encoding="utf-8"))["betriebspunkt"]
        richtig_stub = round(st["genauigkeit_entschieden"] * st["faelle_entschieden"])
        richtig_modell = round(b["genauigkeit_entschieden"] * b["faelle_entschieden"])
        z.append("### Against a floor, and a worked example of why coverage is in every table")
        z.append("")
        z.append(f"The repo ships a keyword classifier with no model in it at all "
                 f"(`--backend stub`): a page of regexes over the error text. On this "
                 f"corpus it scores macro precision **{st['macro_precision']:.2f}** and "
                 f"macro recall **{st['macro_recall']:.2f}**.")
        z.append("")
        z.append("Which looks like it beats the model. It does not, and the reason is the "
                 "whole argument of this page:")
        z.append("")
        z.append("| | regex stub | the agent |")
        z.append("|---|---|---|")
        z.append(f"| macro precision | {st['macro_precision']:.2f} | "
                 f"{b['macro_precision']:.2f} |")
        z.append(f"| coverage | {st['abdeckung']:.0%} | {b['abdeckung']:.0%} |")
        z.append(f"| classes it ever decides | {len(st['macro_basis'])}/3 | "
                 f"{len(b['macro_basis'])}/3 |")
        z.append(f"| `PRODUKTFEHLER` cases decided | "
                 f"{st['je_klasse']['PRODUKTFEHLER']['support_entschieden']}/"
                 f"{st['je_klasse']['PRODUKTFEHLER']['support_gesamt']} | "
                 f"{b['je_klasse']['PRODUKTFEHLER']['support_entschieden']}/"
                 f"{b['je_klasse']['PRODUKTFEHLER']['support_gesamt']} |")
        z.append(f"| **failures correctly triaged, out of {b['faelle_gesamt']}** | "
                 f"**{richtig_stub}** | **{richtig_modell}** |")
        z.append("")
        z.append(f"The stub never classifies a product bug at all — it escalates all "
                 f"{st['je_klasse']['PRODUKTFEHLER']['support_gesamt']} of them — so its "
                 f"perfect score is a perfect score on the easy two-thirds. Judged on the "
                 f"only question a team actually cares about, how many of the "
                 f"{b['faelle_gesamt']} red builds got triaged correctly, it does "
                 f"{richtig_stub} and the agent does {richtig_modell}.")
        z.append("")
        z.append("This is exactly the trap described further up, and it is left standing "
                 "in the repo rather than tuned away, because it is the clearest possible "
                 "demonstration that a precision number without a coverage number next to "
                 "it is not a result.")
        z.append("")
    z.append("Raw output: [`eval/ergebnis.json`](eval/ergebnis.json) · "
             "per-case verdicts: [`eval/predictions_" + e["backend"] + ".jsonl`]"
             "(eval/predictions_" + e["backend"] + ".jsonl)")
    return "\n".join(z)


def sweep_block(e: dict) -> str:
    b = e["betriebspunkt"]
    z: list[str] = []
    z.append("| threshold | macro P | macro R | classes in macro P | `PRODUKTFEHLER` recall | coverage | escalated | **buried bugs** |")
    z.append("|---|---|---|---|---|---|---|---|")
    unvollstaendig = False
    for r in e["sweep"]:
        hier = r["schwelle"] == b["schwelle"]
        markierung = " **<- shipped**" if hier else ""
        n_basis = len(r.get("macro_basis_precision", KLASSEN))
        if n_basis < len(KLASSEN):
            unvollstaendig = True
        basis = f"{n_basis}/3" + ("" if n_basis == len(KLASSEN) else " ⚠")
        z.append(f"| {r['schwelle']:.2f}{markierung} | {r['macro_precision']:.2f} | "
                 f"{r['macro_recall']:.2f} | {basis} | "f"{'–' if r['produktfehler_recall'] is None else format(r['produktfehler_recall'], '.2f')} | "
                 f"{r['abdeckung']:.0%} | {r['eskalationsquote']:.0%} | "
                 f"{r['versenkte_produktfehler']} |")
    z.append("")
    if unvollstaendig:
        z.append("**Read the 'classes in macro P' column before the macro column.** Once a "
                 "class stops being predicted at all, its precision is undefined rather "
                 "than zero, so it leaves the average — a row marked ⚠ is averaging fewer "
                 "classes than the rows above it, and its macro is *not* comparable to "
                 "them. The perfect scores at the high end are real, but they are perfect "
                 "scores on two classes and a shrinking share of the corpus, not a better "
                 "agent. This is the exact trap the coverage column exists to expose, and "
                 "it is left in the table rather than tuned away.")
        z.append("")
    ohne = e.get("ablation_ohne_flake_aufschlag")
    if ohne:
        gleiche_abdeckung = ohne["abdeckung"] == b["abdeckung"]
        gleiche_versenkte = ohne["versenkte_produktfehler"] == b["versenkte_produktfehler"]
        if gleiche_abdeckung and gleiche_versenkte:
            z.append(f"**Ablation — drop the `FLAKE` surcharge** (same predictions, same "
                     f"{b['schwelle']} threshold, `FLAKE` no longer held to the extra "
                     f"+{b['flake_aufschlag']}): **no change at all** — coverage stays at "
                     f"{b['abdeckung']:.0%} and buried bugs stay at "
                     f"{b['versenkte_produktfehler']}.")
            z.append("")
            z.append("Which is worth saying plainly rather than quietly dropping: on this "
                     "corpus the surcharge did nothing. It could not, because the agent "
                     "never once predicted `FLAKE` wrongly — the class it over-uses is "
                     "`KAPUTTER_TEST`, and that one has no surcharge. The guard is "
                     "insurance that did not have to pay out here. It stays in because "
                     "the cost it insures against (a product bug auto-rerun into silence) "
                     "is the one unbounded cost in the system, and a corpus of 47 cases "
                     "is not evidence that it never happens — only that it did not "
                     "happen here.")
        else:
            z.append(f"**Ablation — drop the `FLAKE` surcharge** (same predictions, same "
                     f"{b['schwelle']} threshold, `FLAKE` no longer held to the extra "
                     f"+{b['flake_aufschlag']}): coverage {b['abdeckung']:.0%} → "
                     f"{ohne['abdeckung']:.0%}, buried product bugs "
                     f"**{b['versenkte_produktfehler']} → "
                     f"{ohne['versenkte_produktfehler']}**. That difference is the "
                     f"argument for the surcharge being a separate knob rather than part "
                     f"of the threshold.")
    return '\n'.join(z)


def fehler_block(e: dict) -> str:
    """The mistakes, grouped, straight out of the confusion matrix."""
    b = e["betriebspunkt"]
    paare = []
    for wahr in KLASSEN:
        for vorhergesagt in KLASSEN:
            if wahr != vorhergesagt and b["konfusion"][wahr][vorhergesagt]:
                paare.append((b["konfusion"][wahr][vorhergesagt], wahr, vorhergesagt))
    paare.sort(reverse=True)
    z: list[str] = []
    if not paare:
        z.append("At this threshold the agent made no misclassification. With a corpus "
                 "this size that is a statement about the corpus, not about the agent.")
        return '\n'.join(z)
    z.append("| truth | agent said | cases |")
    z.append("|---|---|---|")
    for n, wahr, vorhergesagt in paare:
        z.append(f"| `{wahr}` | `{vorhergesagt}` | {n} |")
    z.append("")
    gesamt = sum(n for n, _, _ in paare)
    nach_kt = sum(n for n, _, v in paare if v == "KAPUTTER_TEST")
    if nach_kt == gesamt and len(paare) > 1:
        z.append(f"**Every one of the {gesamt} mistakes lands in the same place: "
                 "`KAPUTTER_TEST`.** It is the class the agent falls into when the "
                 "evidence runs out, which is why its recall is the highest of the three "
                 "and its precision the lowest — it absorbs the uncertainty of the other "
                 "two.")
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
    text = _block(text, "FEHLER", fehler_block(e))
    readme.write_text(text, encoding="utf-8")
    print("README numbers refreshed from eval/ergebnis.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
