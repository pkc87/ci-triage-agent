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
<!-- SCHWELLE:ENDE -->

---

## What this agent cannot do

<!-- GRENZEN:START -->
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
