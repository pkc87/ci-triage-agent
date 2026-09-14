# Case format (contract between corpus producers and the eval)

Every triage case is one directory under `eval/cases/<id>/`.

```
eval/cases/<id>/
  fall.json        required  structured evidence bundle
  diff.patch       required  the change under test (git diff text; may be truncated)
  report.json      optional  raw Playwright JSON report slice for this one test
  trace.txt        optional  human-readable action log extracted from trace.zip
  screenshot.png   optional  failure screenshot
```

## fall.json

```jsonc
{
  "id": "syn-014",
  "quelle": "synthetisch",              // "synthetisch" | "historisch"
  "repo": "fixtures/shop",              // where the failure came from
  "test_titel": "checkout shows the total",
  "test_datei": "tests/checkout.spec.ts",
  "test_zeile": 42,
  "fehlermeldung": "<full Playwright error text, ANSI stripped>",
  "stack": "<stack / code frame, may be empty>",
  "dauer_ms": 1234,
  "versuche": [ {"nr": 1, "status": "failed"}, {"nr": 2, "status": "passed"} ],
  "artefakte": { "trace": "trace.txt", "screenshot": "screenshot.png", "diff": "diff.patch" },
  "kontext": { "branch": "feat/x", "commit": "abc1234", "ci_lauf": "https://..." }
}
```

`versuche` must reflect what actually happened. A test that genuinely passed on
retry records that; nothing here is invented.

## ground_truth.jsonl

One JSON object per line, appended to `eval/ground_truth.jsonl`:

```jsonc
{
  "id": "syn-014",
  "label": "KAPUTTER_TEST",             // PRODUKTFEHLER | KAPUTTER_TEST | FLAKE
  "quelle": "synthetisch",
  "gelabelt_von": "konstruktion",       // see below
  "begruendung_label": "mutation sel-03 renamed data-testid; product behaviour unchanged",
  "mutation": "sel-03"                  // synthetic only; omit for historical
}
```

`gelabelt_von` values in use:

* `konstruktion` — the label follows from the mutation that produced the case.
  The strongest ground truth available: we know what we broke.
* `historie` — the label follows from external repo evidence (the commit that
  later fixed it, the PR discussion), not from reading the failure alone.
* `claude-opus-5` — assigned by a model from the artifact. Weakest; must be
  disclosed in the README, because it is the same model family under test.

## Label definitions (must be applied literally)

* **PRODUKTFEHLER** — the application behaves wrongly. The test is right, the
  code is wrong. Fixing the product makes the test pass.
* **KAPUTTER_TEST** — the application is fine; the test, its fixtures, its
  baselines or the CI environment are wrong or stale. Fixing the test makes it
  pass and no user was ever affected. Infrastructure failures (missing browser
  binary, broken container, absent env var) fall here: the product is not at
  fault. This boundary is deliberate and is documented in the README.
* **FLAKE** — the same code passes and fails without changing. Nondeterminism:
  races, timing, animation, network jitter, test-order coupling.
