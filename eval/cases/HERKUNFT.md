# Provenance of the historical cases (`hist-*`)

This file documents where the `hist-*` cases come from, how they were sampled, and
what each label rests on. It is deliberately uncomfortable: the corpus carries a
public precision/recall claim, and the weaknesses below are part of the reading.

## Source

Nine failed `ci-test` runs from the **private** monorepo
`KornmuellerConsulting/apps`, all from the app `apps/kc-web` (Astro company website,
Playwright). These are the repo owner's own projects; publishing excerpts is
authorized.

| CI run | Date | Branch | Head commit | Failures in run | PR |
|---|---|---|---|---|---|
| 34139279743 | 2026-09-07 | `claude/neue-website-bauen-98626e` | `ae8cec99` | 120 | #134 |
| 34142330079 | 2026-09-07 | `claude/neue-website-bauen-98626e` | `05f19739` | 120 | #134 |
| 34144406466 | 2026-09-07 | `claude/neue-website-bauen-98626e` | `e69bf5f6` | 120 | #134 |
| 34144629087 | 2026-09-07 | `claude/neue-website-bauen-98626e` | `3c72202e` | 120 | #134 |
| 34147293024 | 2026-09-07 | `claude/neue-website-bauen-98626e` | `ea499944` | 120 | #134 |
| 34207139258 | 2026-09-08 | `fix/KC-016-cloudflare-dmarc` | `811bc1dc` | 12 | #135 |
| 34207848044 | 2026-09-08 | `fix/KC-016-cloudflare-dmarc` | `c135d351` | 12 | #135 |
| 34210053878 | 2026-09-08 | `fix/KC-016-cloudflare-dmarc` | `da6194ac` | 16 | #135 |
| 34213646399 | 2026-09-08 | `fix/KC-016-cloudflare-dmarc` | `4c6e53a1` | 16 | #135 |

Total: **656 raw failures**.

The nine runs are **not reruns of the same commit** — each has its own head commit.
That matters for the labels: differences between two runs here are explained by real
code changes, not by nondeterminism.

## How the raw data was processed

Logs via `gh run view --log`. Every line carries the prefix
`job<TAB>step<TAB>ISO-timestamp`; that was stripped, as were ANSI sequences
(present in the logs: 60 to 366 affected lines per file). A failure block
starts at `##[error]  N) [project] › file:line:col › title` and ends at the
next such header.

The **last** block of each run runs straight into the Playwright run summary in the
log (`##[notice]  120 failed`, the list of all failed titles, the pnpm exit line).
That summary was cut off: it belongs to the run, not to the individual failure, and
it would have given individual cases a list of sibling failures that none of the
other cases have — a fairness problem for the evaluation. After that, all excerpts
within a cluster are the same length (14 and 36 lines respectively).

## How many root causes this really is

**Two.** No more.

**Root cause A — Playwright browsers were missing in CI (600 raw failures).**
Across all five runs from 2026-09-07 the error text is **byte-identical**:
`browserType.launch: Executable doesn't exist at …/chrome-headless-shell`.
Measured: the set of titles of the 120 failures is identical in all five runs,
and across all 600 failures there is exactly **one** distinct error text.
Variation exists only in test title, line number and route.

**Root cause B — Linux baselines out of date (56 raw failures).**
All four runs from 2026-09-08 are `toHaveScreenshot` deviations from the same
test file `tests/visual/layout.spec.ts:33`. Two manifestations:
a height difference (`Expected an image 1440px by 3760px, received 1440px by 3782px`)
and identical dimensions with a pixel deviation above the threshold
`maxDiffPixelRatio: 0.001` set in the test. Both go back to the same cause (see below)
and were **not** counted as two root causes.

## Sampling

The goal was "at most 18 cases, at most 7 per root cause". With exactly two root
causes the ceiling is therefore **14** — and 14 cases were drawn, 7 per root cause.

The missing 4 were **deliberately not** filled in. To get to 18, root cause B would
have had to be split into "height difference" and "pixel difference at identical
size". Those are two manifestations of **one** cause; separating them would have
raised the number and watered down the claim.

Cases were drawn for maximum diversity of evidence, not at random:

**Root cause A (hist-001 … hist-007)** — the quality suite has six distinct
assertion sites (lines 43, 68, 79, 89, 99, 105). One case was drawn **per
site**, plus a second one at line 79 with a different viewport and a different route.
Spread across **all five** head commits, so that each case carries a different
`diff.patch`.

| Case | Run | Line | Test title |
|---|---|---|---|
| hist-001 | 34139279743 | 43 | `/ — jedes Bild rendert mit echter Breite` |
| hist-002 | 34142330079 | 68 | `/es — keine Konsolenfehler` |
| hist-003 | 34144406466 | 79 | `/projekte — kein Querlauf (mobil)` |
| hist-004 | 34144629087 | 79 | `/en/services — kein Querlauf (tablet)` |
| hist-005 | 34147293024 | 89 | `/datenschutz — Seite bleibt unter 500 KB` |
| hist-006 | 34139279743 | 99 | `/unternehmen — genau eine H1` |
| hist-007 | 34142330079 | 105 | `kein Fremd-CDN, kein Tracker, kein jQuery` |

**Root cause B (hist-008 … hist-014)** — drawn across six different routes, both
viewports, both manifestations, all four head commits, and across the whole
range of pixel ratios (0.01 to 0.17).

| Case | Run | Route/viewport | Evidence |
|---|---|---|---|
| hist-008 | 34207139258 | `/es` desktop | 1440×3760 → 3782, 55043 px, 0.02 |
| hist-009 | 34207139258 | `/datenschutz` mobil | 390×3108 → 3179, 126760 px, 0.11 |
| hist-010 | 34207848044 | `/es/servicios` desktop | 1440×2820 → 2898, 459603 px, 0.12 |
| hist-011 | 34210053878 | `/unternehmen` desktop | same size, 22726 px, 0.01 |
| hist-012 | 34210053878 | `/en/company` mobil | same size, 4330 px, 0.01 |
| hist-013 | 34213646399 | `/unternehmen` desktop | 1440×3404 → 3439, 460404 px, 0.10 |
| hist-014 | 34213646399 | `/es/empresa` mobil | 390×4894 → 4986, 326032 px, 0.17 |

Two cases are in there on purpose, because they are triage traps:

* **hist-010** — the head commit `c135d351` changes **only**
  `apps/kc-web/scripts/deploy-cf.mjs`, a file that appears in no built page.
  The failure is byte-identical to the one from the previous run. Anyone who takes
  the diff under test to be the cause is demonstrably wrong here.
* **hist-011 / hist-013** — same test, same cause, two consecutive commits, but a
  completely different evidence picture (22726 px at identical size versus
  460404 px with a height difference).

## Labels and what they rest on

**All 14 cases: `KAPUTTER_TEST`, all `gelabelt_von: "historie"`.**
No case rests on a model judgement. No `claude-opus-5` label in the corpus.

**Root cause A** — the fix is `34b8d949e2b45e72a3f702e3a134a8094f505b4f` (PR #134):
it moves the step `Install Playwright Browsers` **before** the step `Unit-Tests`
in `.github/workflows/ci-test.yaml` and names the incident verbatim in the file
comment: *„Solange dieser Schritt danach stand, scheiterten am 07.09.2026 alle 120
kc-web-Pruefungen mit `browserType.launch: Executable doesn't exist`."*
[As long as this step came after it, on 2026-09-07 all 120 kc-web checks failed with
`browserType.launch: Executable doesn't exist`.] The commit message files it as
REPO-023. What changed was the CI environment — neither product code nor test code.
Per `docs/fallformat.md`, a missing browser binary is explicitly `KAPUTTER_TEST`.

**Root cause B** — the chain of evidence has three parts and was verified in full:

1. `145bad4f629f50c34241e5be11ae334f61c7475a` (PR #136, 2026-09-08) created the 34
   Linux snapshots, recorded on a CI runner from the then-current state of `main`
   (`34b8d949`). Cross-check: `git diff 34b8d949..145bad4 -- apps/kc-web/` is
   **empty** under `src/` — the baselines cleanly reflect the branch's starting state.
2. The PR branch then **deliberately** changed content and, in the same commits,
   refreshed **only the win32 set** of the baselines:
   `811bc1dc` (KC-018, `src/content/es.ts`, 174 corrections → only `es-*-win32.png`),
   `8dcb8ab` (KC-016, `src/pages/datenschutz.astro`, 14 lines),
   `da6194ac` (KC-020, H1 in de/en/es → only `unternehmen-*` and `en-company-*-win32.png`),
   `4c6e53a1` (KC-021, the same H1 again).
   CI runs on `ubuntu-latest` and looks for `*-visual-linux.png`.
3. Resolved on 2026-09-10 by `5f3210fd6f6e946c0de34d636ab018fb267369f1`
   (*„test(KC-038): Linux-Baselines nachgezogen — sie waren aelter als der Umbau"*
   [Linux baselines brought up to date — they were older than the rebuild]):
   **34 changed files, all PNG, 0 lines of code.** Verified with
   `git show --name-only 5f3210f | grep -v '\.png$'` → empty.

A fix that only touches baselines and turns the run green is by definition
`KAPUTTER_TEST`.

## Artifacts per case

```
eval/cases/hist-NNN/
  fall.json         structured evidence
  diff.patch        real git diff, merge-base..head, truncated
  log_excerpt.txt   verbatim, de-ANSI'd failure block from the CI log
```

* **No `report.json`.** There is no Playwright JSON report in the logs
  (`reporter: 'github'` in `playwright.config.ts`). Rather than invent one,
  `artefakte` references the log excerpt as `{"ci_log": "log_excerpt.txt"}`.
* **No `trace.txt`, no `screenshot.png`.** `trace: 'retain-on-failure'` is set,
  but the artifacts were never uploaded and can no longer be retrieved.
* **`dauer_ms` is `null`.** The `github` reporter does not print a runtime per test.
  The key stays for schema fidelity; the value is honestly unknown.
* **`versuche` is `[{"nr": 1, "status": "failed"}]` everywhere.** Checked against all
  nine commits: `retries: 0` in `apps/kc-web/playwright.config.ts`. There was exactly
  one attempt. No case invents a retry.

### diff.patch — what is in it and what is not

Generated with `git diff <merge-base(main, head)>..<head>`, truncated to ~400 lines at
the nearest file boundary, with an explicit `[... truncated N lines ...]` marker
that names the full command. All patches parse with `git apply --stat`.

Merge base per cluster: `fed35e0d` (2026-09-07), `34b8d949` (2026-09-08).

**Two files are excluded from every patch via git pathspec:**
`apps/kc-web/BLOCKERS.md` and `apps/kc-web/DECISIONS.md`. Both name a reference
customer by name whose written approval was still outstanding at that point. This is
a declared redaction, not a forgery: every patch carries it in the footer marker.
Nothing else was changed. Side effect: the 400-line window therefore reaches as far
as `playwright.config.ts` and `package.json` — the redaction raised the information
content, it did not lower it.

The entire shipped content was checked for token patterns (`ghp_`, `sk-`,
`AKIA`, `xox*`, PEM headers), `***`-masked lines, email addresses and
customer names. Hits: none. The remaining occurrences of „Referenzkunden"
[reference customers] are counts („dreizehn Referenzkunden" — thirteen reference
customers), not names.

## Weaknesses — read these too

1. **A single class.** All 14 cases are `KAPUTTER_TEST`. There are **zero**
   `PRODUKTFEHLER` and **zero** `FLAKE`. A classifier that blindly guesses
   "KAPUTTER_TEST" scores 100% on this sub-corpus. On their own, the `hist-*`
   cases can carry **no** precision/recall claim; they only make sense together
   with the synthetic cases, and the class distribution of the full corpus has to
   be stated in the README.
2. **Only two root causes and one app.** 656 raw failures collapse into two
   root causes, both from `apps/kc-web`, both Playwright. This is not a cross-section
   of CI failures, it is two well-documented incidents.
3. **No FLAKE, even though it looked like one at first.** Between run 34210053878 and
   34213646399 the pixel counts of the same test change (22726 → 460404). That
   looked like nondeterminism, but it is fully explained by different head commits
   (`da6194ac` vs. `4c6e53a1`, both changing the same H1).
   It was **not** labelled FLAKE. Without a rerun of the same commit, flakiness
   cannot be demonstrated from this data.
4. **The diff under test never contains root cause A.** In the seven
   browser-binary cases the cause sits in the workflow, which at the time of the run
   was not in the diff at all. An agent can only solve these cases via the error
   text, not via the diff. That is realistic, but it makes `diff.patch` context
   there rather than evidence.
5. **CI tested the PR merge commit, not the head commit.** The logs show
   `Merge <head> into <base>` against `refs/remotes/pull/<n>/merge`. `kontext.commit`
   carries the head commit (what was pushed); the CI base differed from it —
   for PR #135 it was `145bad4` or `9f571b3`, not the merge base `34b8d949`.
   Cross-checked: between `145bad4` and `9f571b3`, `main` touched nothing under
   `apps/kc-web/`, so the labels are unaffected.
6. **Two test titles appear twice.** hist-011 and hist-013 carry the same
   `test_titel` (different runs/commits). Anyone deduplicating by title instead of by
   `id` will count wrong here.
