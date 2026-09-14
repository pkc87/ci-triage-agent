# Decisions

Why this is built the way it is. Written while building, not reconstructed
afterwards. Where a decision is a guess, it says so.

---

## 1. The model classifies. The system decides.

The model returns `klasse`, `konfidenz`, `begruendung`, `beleg`. It never returns
`aktion`. The action is derived by `agent/schema.py:entscheide()` from the
confidence and a threshold.

**Why.** If the model picked the action, the threshold would be baked into the
inference. Every row of the threshold sweep would need its own inference run —
ten times the cost, and every row would carry a different sample of model
noise, so the rows would not be comparable. With the split, the sweep is pure
arithmetic over one stored set of predictions: differences between rows are the
*policy* changing and nothing else.

It also means the operating point can be retuned in production without touching
the prompt or re-validating the model.

---

## 2. Three classes, not more — and infrastructure failures go in `KAPUTTER_TEST`

The real CI history that seeded this corpus contains a large cluster that is
none of the three cleanly: `browserType.launch: Executable doesn't exist` —
Playwright browsers were never installed on the runner. The product is fine.
The test is fine. The *machine* is broken.

The honest options were a fourth class (`INFRA`) or a documented boundary.
Chose the boundary: **if the error is about the machinery that runs the test
rather than the software under test, it is `KAPUTTER_TEST`.** The class is
defined by *who has to fix it and whether a user was affected*, and on both
counts infra sits with the test, not the product.

This is a real limitation, not a clean win. A team that wants to route infra
failures to a platform group rather than the test owner needs a fourth class,
and adding one means relabelling the corpus. It is called out in the README
under limitations rather than buried here.

---

## 3. The threshold favours recall, and `FLAKE` carries a surcharge

The default operating point is **0.70**, with `FLAKE` needing **0.80**
(`FLAKE_AUFSCHLAG = 0.10`).

The three wrong answers are not equally expensive:

| what happens | cost |
|---|---|
| product bug → `TICKET` with the wrong class | someone reads a ticket and reclassifies it. Minutes. |
| anything → `ESKALATION_MENSCH` | exactly the status quo. A human triages it, as they do today. |
| **product bug → `RERUN`** | the failure disappears, the board goes green, the bug ships. |

Only the last one is actually dangerous, and `RERUN` is the only action that
produces it. So `RERUN` — which only a `FLAKE` verdict can trigger — gets a
higher bar than the other two. Everything else is allowed to be wrong more
cheaply.

This is why the headline metric is not accuracy. It is
`versenkte_produktfehler`: the count of real product bugs the agent auto-reran
into silence. Everything else is a tradeoff; that number is a floor.

The sweep in `eval/ergebnis.json` shows the surcharge's effect directly — the
`ablation_ohne_flake_aufschlag` block is the same predictions scored with the
surcharge set to zero.

---

## 4. Escalated cases are excluded from precision and recall, and coverage is always printed next to them

An abstention is not a wrong answer, and scoring it as one would punish the
behaviour this project is trying to demonstrate. So precision and recall are
computed over *decided* cases only.

That metric is trivially gameable on its own: escalate 98% of cases and the
remaining 2% will look superb. So it is never reported on its own. Coverage and
the escalation rate sit in the same table, in every output this repo produces,
and a class that was escalated entirely is dropped from the macro average
rather than scored as zero — with the classes actually averaged listed in
`macro_basis` so the reader can see what went into it.

---

## 5. An unparseable verdict escalates. It is never repaired into a class.

Models occasionally answer in prose. `parse_verdict` rejects anything that is
not a well-formed verdict with a known class and an in-range confidence; the
agent retries once and then gives up and escalates.

The tempting shortcut — regex the class name out of the prose — would push
noise straight into the precision number. Parse failures are counted separately
in `ergebnis.json` as `parse_fehler` so the reader can see how often it
happened.

---

## 6. The corpus is half real and half constructed, and the split is published

Real CI history was the first choice. What it actually yielded:
596 individual failing tests across nine runs — which collapse into **three**
root causes. Real CI failures cluster hard: one broken runner config produces
120 identical failures, and rerunning it five times produces 600.

Three root causes cannot support a per-class precision claim. So the historical
half is a documented *sample* (capped per root cause so no cluster dominates),
and the rest of the corpus is built by deliberately breaking a fixture app.

Constructed cases have one property real ones do not: the label is known by
construction. We know what we broke, so `gelabelt_von: "konstruktion"` is the
strongest ground truth in the corpus, not the weakest. The weak labels are the
historical ones that rest on model judgement, and they are marked
`gelabelt_von: "claude-opus-5"` precisely so a reader can discount them.

Every generated case comes from a real Playwright run against a real mutated
app. No report was written by hand.

---

## 7. Flakes had to be genuinely nondeterministic

A "flake" that fails every single time is not a flake, it is a broken test with
timing-flavoured wording. Mutations in the `FLAKE` class were each run
repeatedly and the observed failure rate recorded in the mutation metadata. The
retry log in each case (`versuche`) is whatever actually happened — a case that
shows `failed → passed` genuinely did that on an unchanged commit.

That signal is also the single strongest cue available to the agent, which
creates an obvious risk: a corpus where every flake shows a retry-pass and
nothing else does would make `FLAKE` detection trivial and the number
meaningless. The historical cases are the counterweight — `kc-web` runs with
`retries: 0`, so those cases carry no retry signal at all.

---

## 8. Three backends

`api` (Anthropic SDK) is the reproduction path. `cli` (Claude Code headless)
runs on a subscription with no API key. `stub` is a keyword classifier with no
model at all.

The stub is not a vanity baseline — it exists so that `.github/workflows/ci.yml`
can run the entire pipeline on every pull request with no secret and no spend.
It proves the corpus loads, every case parses, the metrics compute and the
sweep runs. It is also, usefully, a floor: a prompt that cannot beat a page of
regexes is not earning its latency.

Which backend produced the published numbers is stated in the README and in
`ergebnis.json`, not hidden.

---

## 9. No eval framework

promptfoo and DeepEval were both candidates. The metric is a confusion matrix
and two ratios — about sixty lines in `eval/metrics.py`, with unit tests that
check the arithmetic against hand-computed values.

A framework here would add a dependency, a config format and a layer of
indirection between the reader and the number, in exchange for nothing this
project needs. The whole point is that someone can open one file and check the
number themselves.

---

## 10. Text-only evidence in the published run

Screenshots are collected and the `api` backend can send them
(`--mit-screenshot`). The headline run is text-only, because that keeps the
comparison clean and the cost per failure low.

Whether the screenshot earns its tokens is an open question, measured rather
than asserted — see the README's limitations section for where that stands.

---

## 11. A prediction, written down before the corpus was scored

Error analysis after the fact is easy to bend into a story. So here is the
failure mode predicted in advance, on 2026-09-14, from a single hand-built probe
case run during development — before the corpus existed and before any scored
run.

The probe was a product bug: `Math.round` changed to `Math.floor` in a tax
calculation, and a test asserting the correctly-rounded total. Ground truth:
`PRODUKTFEHLER`. The agent answered `KAPUTTER_TEST` at 0.85, reasoning that the
diff "deliberately changes the tax rounding logic" and the test therefore
asserts stale behaviour.

That is the right reasoning applied to the wrong premise. Nothing in a diff
says whether a change was intended — a deliberate-looking edit and a careless
one look identical in a patch. The prompt explicitly asks the model to "read the
diff for intent", which is precisely the instruction that produces this.

**Predicted systematic error: `PRODUKTFEHLER` misread as `KAPUTTER_TEST`
whenever the change under test looks purposeful.** The asymmetry matters —
`KAPUTTER_TEST` still produces a `TICKET`, so a human sees it and the bug is
not buried. It costs a misfiled ticket, not a shipped regression.

Whether this survived contact with the corpus is in the README's error
analysis. If it did not, that is recorded too.
