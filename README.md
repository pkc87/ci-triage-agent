# ci-triage-agent

An agent that triages red CI builds — and hands back the ones it cannot call.

---

## The problem

A Playwright suite goes red. Somebody has to open the report and decide which
of three things happened: the product actually broke, a test broke, or nothing
broke and the run was flaky. That decision takes a few minutes, it happens
several times a day on any team with real test automation, and it is the reason
teams eventually stop looking at red builds at all.

This agent makes that call, attaches a confidence to it, and — below a
threshold — refuses to make it and escalates to a human instead.

---

## What it decides

Input: a failing Playwright test — the report JSON, the trace, the screenshot,
and the diff of the change under test.

Output, per failure:

```
klasse:      PRODUKTFEHLER | KAPUTTER_TEST | FLAKE
konfidenz:   0.0 - 1.0
begruendung: two sentences, citing the evidence
aktion:      RERUN | TICKET | ESKALATION_MENSCH
```

<!-- BEISPIEL:START -->
A real verdict from the run below (case `syn-019`, ground truth `PRODUKTFEHLER`):

```
klasse:      PRODUKTFEHLER
konfidenz:   0.95
begruendung: The diff shows clampQuantity was changed from `return Math.max(1, parsed)` to `return parsed`, removing the clamping logic entirely, so a quantity of -3 is now passed straight through instead of being floored to 1. The test's assertion is exactly about this clamping behavior, and a function named clampQuantity that no longer clamps is a regression a real user would hit, not a stale test.
beleg:       -  return Math.max(1, parsed); +  return parsed;
aktion:      TICKET
```

`beleg` is a literal quote from the evidence, required by the prompt. A verdict the model cannot cite is a verdict it does not have — it is the cheapest guard against confident nonsense in the whole system.
<!-- BEISPIEL:ENDE -->

**The escalation is the point.** Below the confidence threshold the agent does
not decide. It hands the failure to a person, which is exactly the status quo
and therefore costs nothing. An agent that knows when it doesn't know is the
difference between a toy and a tool — and it is the only reason a team would
let one near their CI.

The model never chooses the action. It returns a class and a confidence; the
action is derived by policy (`agent/schema.py`). That separation is what makes
the threshold sweep below honest: every row is the same model output scored
under a different policy, not ten separate runs that could each have drifted.

Glossary, since the field names are German: `klasse` = class, `konfidenz` =
confidence, `begruendung` = rationale, `beleg` = citation, `aktion` = action.
`PRODUKTFEHLER` = product bug, `KAPUTTER_TEST` = broken test.

---

## The numbers

<!-- ZAHLEN:START -->
**47 labelled failures** — 14 pulled from real CI history, 33 produced by deliberately breaking a fixture app. Scored with `cli` backend, model `claude-sonnet-5`, at threshold **0.7**.

| Class | Precision (95% CI) | Recall (95% CI) | F1 | Cases | Decided | Escalated |
|---|---|---|---|---|---|---|
| `PRODUKTFEHLER` | 1.00 <sub>[0.68-1.00]</sub> | 0.53 <sub>[0.30-0.75]</sub> | 0.70 | 15 | 15 | 0 |
| `KAPUTTER_TEST` | 0.67 <sub>[0.50-0.80]</sub> | 1.00 <sub>[0.85-1.00]</sub> | 0.80 | 25 | 22 | 3 |
| `FLAKE` | 1.00 <sub>[0.34-1.00]</sub> | 0.33 <sub>[0.10-0.70]</sub> | 0.50 | 7 | 6 | 1 |
| **macro** | **0.89** | **0.62** | **0.67** | 47 | 43 | 4 |

The intervals are Wilson score intervals, and they are wide because the corpus is small. That is the honest shape of this result: the point estimates are real measurements, and a per-class number resting on a dozen cases cannot be quoted to two decimals as though it were stable. If you only take one number from this table, take the interval.

Coverage **91%** (the agent decided that share of cases and escalated the rest) · accuracy on decided cases **74%** · unparseable verdicts: 0

**Product bugs silently auto-rerun: 0.** That is the number this system is tuned around; see the threshold section.

Precision and recall are computed over *decided* cases only — an escalation is an abstention, not a wrong answer. Reported alone that would be trivially gameable (escalate everything, look perfect on the remainder), so coverage sits in the same table and never leaves it.

### Confusion matrix

Rows are the true label, columns are what the agent actually did.

| truth \ agent | `PRODUKTFEHLER` | `KAPUTTER_TEST` | `FLAKE` | escalated |
|---|---|---|---|---|
| **`PRODUKTFEHLER`** | 8 | 7 | 0 | 0 |
| **`KAPUTTER_TEST`** | 0 | 22 | 0 | 3 |
| **`FLAKE`** | 0 | 4 | 2 | 1 |

### How much of this is the dice?

The same corpus was run through the same model twice. Across the 47 cases both runs answered, they agreed on the class **89%** of the time and on the resulting action **100%** of the time, with a mean confidence difference of **0.029**.

The gap between those two numbers is the interesting part: the cases that flip flip between `PRODUKTFEHLER` and `KAPUTTER_TEST`, and both of those produce a `TICKET`. So the instability is real in the classification and invisible in what a team would actually experience. That is a property of the action policy, not luck — the two classes the agent confuses are the two that cost the same to be wrong about.

Sampling is not deterministic, so a single run reports one draw from a distribution. The point of measuring this is calibration of a different kind: it sets the size of difference that is worth believing. A prompt change that moves macro precision by less than this is noise, and this repository is not going to claim otherwise. `eval/stabilitaet.json` has the per-case detail.

### Does the confidence mean anything?

Everything above rests on one assumption: that the number the model reports tracks how often it is actually right. If it does not, the threshold sorts by noise and every sweep row is theatre. So here is the assumption, checked:

| stated confidence | cases | correct | hit rate (95% CI) |
|---|---|---|---|
| 0.00 – 0.60 | 4 | 2 | 50% <sub>[15%–85%]</sub> |
| 0.60 – 0.75 | 1 | 0 | 0% <sub>[0%–79%]</sub> |
| 0.75 – 0.90 | 11 | 6 | 55% <sub>[28%–79%]</sub> |
| 0.90 – 1.00 | 31 | 26 | 84% <sub>[67%–93%]</sub> |

Read this before the headline table.

### Where the data comes from

Class balance: `FLAKE` 7, `KAPUTTER_TEST` 25, `PRODUKTFEHLER` 15. Label provenance: `historie` 14, `konstruktion` 33.

- `konstruktion` — the label follows from the mutation that produced the failure. We know what we broke, so this is the strongest ground truth here, not the weakest.
- `historie` — the label follows from external repo evidence: the commit that later fixed it.
- `claude-opus-5` — assigned by a model reading the artefact. **No case in this corpus carries this label.** The value exists in the schema because it was the expected fallback; it turned out not to be needed, and that is worth more than the fallback would have been.

The constructed half is not a shortcut, it is a necessity, and the reason is worth stating plainly: **real CI failures cluster, hard.** The nine failed runs behind the historical cases contain **656** individual failing tests that collapse into exactly **two** root causes — one misconfigured runner produced 120 identical failures, and it survived five successive commits before anyone fixed it, for 600 failures with a single distinct error body between them. Two root causes cannot support a per-class precision claim, so the historical half is capped at seven cases per cause and the rest of the corpus is built by breaking a fixture app on purpose.

They were also all one class. Every red build in that history was a broken test or a broken runner: **no product bugs and no flakes at all**. Which is its own small argument for the tool — the humans triaging those builds spent their attention on failures that never reached a user — but it means the `PRODUKTFEHLER` and `FLAKE` rows above rest entirely on constructed cases.

Every synthetic case is a real Playwright run against a really-mutated app. No report in this repo was written by hand. `eval/cases/HERKUNFT.md` records which CI runs the historical cases came from and how they were sampled.

### Against a floor, and a worked example of why coverage is in every table

The repo ships a keyword classifier with no model in it at all (`--backend stub`): a page of regexes over the error text. On this corpus it scores macro precision **1.00** and macro recall **1.00**.

Which looks like it beats the model. It does not, and the reason is the whole argument of this page:

| | regex stub | the agent |
|---|---|---|
| macro precision | 1.00 | 0.89 |
| coverage | 40% | 91% |
| classes it ever decides | 2/3 | 3/3 |
| `PRODUKTFEHLER` cases decided | 0/15 | 15/15 |
| **failures correctly triaged, out of 47** | **19** | **32** |

The stub never classifies a product bug at all — it escalates all 15 of them — so its perfect score is a perfect score on the easy two-thirds. Judged on the only question a team actually cares about, how many of the 47 red builds got triaged correctly, it does 19 and the agent does 32.

This is exactly the trap described further up, and it is left standing in the repo rather than tuned away, because it is the clearest possible demonstration that a precision number without a coverage number next to it is not a result.

Raw output: [`eval/ergebnis.json`](eval/ergebnis.json) · per-case verdicts: [`eval/predictions_cli.jsonl`](eval/predictions_cli.jsonl)
<!-- ZAHLEN:ENDE -->

---

## Where the threshold sits, and why

<!-- SCHWELLE:START -->
**0.70**, with `FLAKE` held to a higher bar of **0.80**.

That is not a tuned number. It follows from the fact that the three ways of
being wrong do not cost the same:

| what happens | what it costs |
|---|---|
| a product bug gets `TICKET` under the wrong class | somebody reads the ticket and reclassifies it. Minutes. |
| anything at all gets `ESKALATION_MENSCH` | exactly today's process. A human triages it, as they already do. |
| **a product bug gets `RERUN`** | the failure vanishes, the board goes green, the bug ships. |

Only the third one is actually dangerous, and only one action produces it —
`RERUN`, which only a `FLAKE` verdict can trigger. So `FLAKE` carries a
surcharge and everything else is allowed to be wrong more cheaply. Escalating
too often is not a failure mode, it is the status quo; the agent has to beat
"a human looks at it", not "nothing happens".

This is why the headline metric is not accuracy. It is **buried product bugs**:
real product failures the agent auto-reran into silence. Everything else on
this page is a tradeoff. That number is a floor.

<!-- SWEEP:START -->
| threshold | macro P | macro R | classes in macro P | `PRODUKTFEHLER` recall | coverage | escalated | **buried bugs** |
|---|---|---|---|---|---|---|---|
| 0.50 | 0.89 | 0.61 | 3/3 | 0.53 | 98% | 2% | 0 |
| 0.55 | 0.89 | 0.61 | 3/3 | 0.53 | 96% | 4% | 0 |
| 0.60 | 0.89 | 0.62 | 3/3 | 0.53 | 91% | 9% | 0 |
| 0.65 | 0.89 | 0.62 | 3/3 | 0.53 | 91% | 9% | 0 |
| 0.70 **<- shipped** | 0.89 | 0.62 | 3/3 | 0.53 | 91% | 9% | 0 |
| 0.75 | 0.90 | 0.63 | 3/3 | 0.57 | 89% | 11% | 0 |
| 0.80 | 0.90 | 0.64 | 3/3 | 0.58 | 83% | 17% | 0 |
| 0.85 | 0.91 | 0.63 | 3/3 | 0.64 | 74% | 26% | 0 |
| 0.90 | 0.89 | 0.57 | 2/3 ⚠ | 0.70 | 62% | 38% | 0 |
| 0.95 | 1.00 | 1.00 | 2/3 ⚠ | 1.00 | 34% | 66% | 0 |

**Read the 'classes in macro P' column before the macro column.** Once a class stops being predicted at all, its precision is undefined rather than zero, so it leaves the average — a row marked ⚠ is averaging fewer classes than the rows above it, and its macro is *not* comparable to them. The perfect scores at the high end are real, but they are perfect scores on two classes and a shrinking share of the corpus, not a better agent. This is the exact trap the coverage column exists to expose, and it is left in the table rather than tuned away.

**Ablation — drop the `FLAKE` surcharge** (same predictions, same 0.7 threshold, `FLAKE` no longer held to the extra +0.1): **no change at all** — coverage stays at 91% and buried bugs stay at 0.

Which is worth saying plainly rather than quietly dropping: on this corpus the surcharge did nothing. It could not, because the agent never once predicted `FLAKE` wrongly — the class it over-uses is `KAPUTTER_TEST`, and that one has no surcharge. The guard is insurance that did not have to pay out here. It stays in because the cost it insures against (a product bug auto-rerun into silence) is the one unbounded cost in the system, and a corpus of 47 cases is not evidence that it never happens — only that it did not happen here.
<!-- SWEEP:ENDE -->

The sweep is honest arithmetic, not ten re-runs: the model is called once per
case, the confidences are stored, and every row re-derives its actions from the
same stored numbers. Rows differ because the policy differs, never because the
model drifted between them.

Pick a different point for a different team. A team with a large flaky suite
and a high tolerance for missed regressions should move left and accept the
buried-bug count that comes with it. `python eval/run_eval.py --nur-auswerten
--schwelle 0.85` re-scores the whole corpus under any policy without spending a
token.
<!-- SCHWELLE:ENDE -->

---

## What it gets wrong

<!-- FEHLER:START -->
| truth | agent said | cases |
|---|---|---|
| `PRODUKTFEHLER` | `KAPUTTER_TEST` | 7 |
| `FLAKE` | `KAPUTTER_TEST` | 4 |

**Every one of the 11 mistakes lands in the same place: `KAPUTTER_TEST`.** It is the class the agent falls into when the evidence runs out, which is why its recall is the highest of the three and its precision the lowest — it absorbs the uncertainty of the other two.
<!-- FEHLER:ENDE -->

`KAPUTTER_TEST` is where the agent goes when it is not sure. It reaches that
conclusion by two different routes, and the citations it produced make both
visible.

**Route one: intent read out of a diff that does not contain it.** Seven real
product bugs were filed as stale tests. In several the mutation shipped the bug
under a plausible comment — `// never charge a fraction of a cent` above a
rounding change that *was* the bug — and the agent quoted that comment back as
its evidence that the change was a considered pricing decision, concluding the
test must be the thing that had not kept up.

The prompt asks it to read the diff for intent, because that genuinely is how
you separate a stale test from a regression. The catch is that **a patch does
not record intent.** A careless change and a considered one are identical in a
diff, and a confident comment above a bug looks exactly like a confident comment
above a feature. The agent is not reasoning badly; it is leaning on a signal
that does not carry the information it needs.

**Route two: missing evidence, not bad reasoning.** Four of the seven flakes
were called broken tests, and the corpus separates cause from symptom cleanly.
Where the retry log showed a pass on the same commit, the agent said `FLAKE` and
was right — twice out of twice. Where every attempt in the run failed, it never
once said `FLAKE` — five out of five. A perfect split on a single field. Flake
detection here is, in effect, a lookup of that field, and a human handed the
same bundle could not do better, because the run's artefacts genuinely do not
contain the answer. Fixing it needs cross-run history for that test, which this
agent does not have and which is the obvious next thing to build.

**The errors are cheap, and that is by construction.** Both routes end in a
`TICKET`, so a human still sees every one of these failures. Zero product bugs
were auto-rerun into silence, at every threshold in the sweep. The agent
misfiles; it does not bury. That asymmetry is the whole design, and it is the
reason `PRODUKTFEHLER` recall of 0.53 is a disappointing number rather than a
dangerous one.

**What was deliberately not fixed.** Flake recall could be lifted immediately by
relaxing the prompt's demand for positive evidence of nondeterminism, and
product-bug recall by telling the model to distrust comments. Both are one-line
prompt edits, both would very likely improve the table above, and both were
refused. On 47 cases, with run-to-run class agreement at 89%, a one-line edit
that moves a number by a few points is indistinguishable from noise — and a
false `FLAKE` is the only error in this system with unbounded cost, because
`RERUN` is the only action that removes a failure without a human seeing it.
Tuning against a corpus this size until the numbers look better is exactly what
this repository exists to argue against.

**A note on the prediction.** This failure mode was written down before the
corpus was scored — see [`docs/entscheidungen.md`](docs/entscheidungen.md) §11,
committed ahead of the first scored run: *product bugs misread as broken tests
whenever the change under test looks purposeful.* It is now the largest single
error group in the table. Predicting your agent's failure mode in advance and
then measuring it is worth more than a better score you cannot explain.

---

## What this agent cannot do

<!-- GRENZEN:START -->
Ranked by how likely they are to bite you, not by how comfortable they are to
write down.

**It has never seen your repository.** Every case comes from one Astro site and
one deliberately-broken fixture shop, both Playwright, both web. Nothing here
supports a claim about a different framework, a different language, a mobile
suite, or an app with a database. The method transfers; the numbers do not.

**`PRODUKTFEHLER` and `FLAKE` rest entirely on constructed cases.** This is the
sharpest limitation in the repo. The real CI history available to build this
contained *no* product bugs and *no* flakes — every red build in it was a broken
test or a broken runner. So the historical half of the corpus is 100%
`KAPUTTER_TEST`, and the agent's ability to recognise the other two classes is
measured only against failures we created on purpose. Constructed failures are
real Playwright runs against a really-broken app, but we chose what to break,
and we may have broken things in ways that are easier to recognise than what a
production codebase produces at 2am.

**The corpus is small and the intervals say so.** Forty-seven cases across three
classes — 15 / 25 / 7. `FLAKE` rests on seven cases and its row should be read
as a direction, not a measurement; its 95% interval for recall spans most of the
range. The Wilson intervals in the table above are wide throughout, and they are
the honest version of this result.

**A model designed the failures it is being tested on.** No label here rests on
model judgement — the historical labels cite the commit that fixed the failure,
and the constructed ones follow from the mutation. But the mutations themselves
were designed with heavy agent assistance, so the constructed half reflects a
model's idea of how tests break. That is a narrower bias than self-grading, and
it is not zero: a failure mode neither the mutation author nor the triage agent
has thought of is absent from both sides of this evaluation.

**Three classes is a simplification, and the seam shows at infrastructure
failures.** A missing browser binary is filed as `KAPUTTER_TEST` because the
product is not at fault. A team that routes infra failures to a platform group
rather than the test owner needs a fourth class, and adding one means
relabelling the corpus. The reasoning is in
[`docs/entscheidungen.md`](docs/entscheidungen.md).

**Flake detection leans on a signal not every CI has.** The strongest evidence
for `FLAKE` is a test that failed and then passed on retry, unchanged. A suite
configured with `retries: 0` — like the one that produced the historical half of
this corpus — gives the agent none of that, and its flake performance there is
untested rather than good.

**It is not wired into anything.** It reads a prepared case directory and
prints a verdict. It does not watch a CI system, download artefacts, open
tickets or trigger reruns. Those are plumbing, but they are unwritten plumbing,
and "we evaluated the judgement" is not the same claim as "we shipped the loop".

**The published run is text-only.** Screenshots are collected and the API
backend can send them; the headline numbers do not use them. Whether the image
earns its tokens is unmeasured.

**This repo was built with heavy agent assistance, including the fixture app and
its tests.** That is worth stating plainly, because it is the exact failure mode
this project is about:

> Green tests written by the same agent that wrote the code aren't evidence —
> they inherit the same blind spots.

Which is why the evaluation loop exists at all, and why it is the part of this
repo worth reviewing first. The fixture suite passing proves nothing on its own.
What carries weight is that the ground truth is defined by the mutations rather
than by anybody's opinion of the output, that the metric is sixty auditable
lines, and that the failures are published next to the successes.
<!-- GRENZEN:ENDE -->

---

## Running it yourself

```bash
git clone https://github.com/pkc87/ci-triage-agent
cd ci-triage-agent
pip install -r requirements.txt
```

Triage a single failure:

```bash
python -m agent eval/cases/syn-001 --backend api
```

Reproduce the whole evaluation — inference, metrics, confusion matrix, sweep:

```bash
export ANTHROPIC_API_KEY=sk-...
make eval
```

Run the pipeline with no API key and no spend (keyword stub, used by CI):

```bash
make eval-stub
```

Re-score stored predictions under a different policy without calling a model:

```bash
python eval/run_eval.py --nur-auswerten --schwelle 0.85
```

Regenerate the synthetic half of the corpus from scratch — applies each
mutation to the fixture app, runs Playwright, captures what actually failed:

```bash
cd fixtures && npm install && npx playwright install chromium
node generate.mjs
```

### Layout

```
agent/        classification: prompt, schema, backends, action policy
eval/         ground truth, runner, metrics, results
fixtures/     the app that gets deliberately broken, and its Playwright suite
docs/         why it is built this way
```

`.github/workflows/ci.yml` runs the unit tests, the whole eval pipeline against
the stub backend, and the fixture suite unmutated, on every pull request. If the
fixture suite is red without a mutation applied, every synthetic case in the
corpus is suspect — so CI checks that too.

---

## License

MIT. See [LICENSE](LICENSE).
