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
<!-- FEHLER:ENDE -->

Two causes sit behind those numbers, and only one of them is a reasoning error.

**Intent is not visible in a diff.** Several real product bugs were filed as
broken tests because the change under test *looked* deliberate — in one case the
mutation carried the comment `// never charge a fraction of a cent` above a
rounding change that was in fact the bug, and the agent quoted that comment back
as its evidence of intent. The prompt asks it to read the diff for intent,
because that is genuinely how you tell a stale test from a regression; the catch
is that a careless change and a considered one are indistinguishable in a patch.
This error is cheap: a wrong `KAPUTTER_TEST` still produces a `TICKET`, so a
human sees it. It costs a misfiled ticket, not a shipped regression.

**A flake that fails every attempt in a run is not distinguishable from a broken
test.** This one is not a reasoning error, it is missing evidence, and the
corpus separates the two cleanly: where the retry log showed a pass on the same
commit, the agent called `FLAKE` and was right; where every attempt in the run
failed, it called `KAPUTTER_TEST` every time. The split is that clean. So flake
detection here is, in effect, a lookup of one field — and a human handed the
same bundle could not do better, because the run's artefacts genuinely do not
contain the answer. Fixing it needs cross-run history for that test, which this
agent does not have and which is the obvious next thing to build.

**What was deliberately not done about it.** Flake recall could be raised
immediately by relaxing the prompt's demand for positive evidence of
nondeterminism. That trade is refused: a false `FLAKE` is the only error in this
system with unbounded cost, because `RERUN` is the only action that removes a
failure without a human seeing it. Trading the one metric that is currently zero
for a better-looking recall number, on a corpus of this size, is precisely the
tuning this repository exists to argue against.

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

**The corpus is small and the intervals say so.** Roughly fifty cases across
three classes. Per-class numbers rest on a dozen or two each; the Wilson
intervals in the table above are wide, and they are the honest version of the
result.

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
