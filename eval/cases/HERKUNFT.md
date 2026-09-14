# Herkunft der historischen Fälle (`hist-*`)

Diese Datei dokumentiert, woher die `hist-*`-Fälle stammen, wie gesampelt wurde und
worauf jedes Label ruht. Sie ist absichtlich unbequem: der Korpus trägt eine
öffentliche Precision/Recall-Aussage, und die Schwächen unten gehören mitgelesen.

## Quelle

Neun fehlgeschlagene `ci-test`-Läufe aus dem **privaten** Monorepo
`KornmuellerConsulting/apps`, alle aus der App `apps/kc-web` (Astro-Firmenwebsite,
Playwright). Es sind die eigenen Projekte des Repo-Eigentümers; die Veröffentlichung
von Auszügen ist autorisiert.

| CI-Lauf | Datum | Branch | Head-Commit | Fehlschläge im Lauf | PR |
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

Summe: **656 rohe Fehlschläge**.

Die neun Läufe sind **keine Reruns desselben Commits** — jeder hat einen eigenen
Head-Commit. Das ist wichtig für die Labels: Unterschiede zwischen zwei Läufen sind
hier durch echte Codeänderungen erklärt, nicht durch Nichtdeterminismus.

## Wie die Rohdaten verarbeitet wurden

Logs via `gh run view --log`. Jede Zeile trägt das Präfix
`job<TAB>step<TAB>ISO-Zeitstempel`; das wurde entfernt, ebenso ANSI-Sequenzen
(in den Logs vorhanden: 60 bis 366 betroffene Zeilen je Datei). Ein Fehlschlag-Block
beginnt bei `##[error]  N) [projekt] › datei:zeile:spalte › titel` und endet beim
nächsten solchen Header.

Der **jeweils letzte** Block eines Laufs geht im Log unmittelbar in die
Playwright-Laufzusammenfassung über (`##[notice]  120 failed`, die Liste aller
fehlgeschlagenen Titel, die pnpm-Exit-Zeile). Diese Zusammenfassung wurde
abgeschnitten: sie gehört zum Lauf, nicht zum einzelnen Fehlschlag, und hätte
einzelnen Fällen eine Liste der Geschwister-Fehlschläge mitgegeben, die alle anderen
Fälle nicht haben — ein Fairness-Problem für die Auswertung. Danach sind alle
Auszüge je Cluster gleich lang (14 bzw. 36 Zeilen).

## Wie viele Ursachen das wirklich sind

**Zwei.** Nicht mehr.

**Ursache A — Playwright-Browser fehlten in der CI (600 rohe Fehlschläge).**
Über alle fünf Läufe vom 07.09. hinweg ist der Fehlertext **byte-identisch**:
`browserType.launch: Executable doesn't exist at …/chrome-headless-shell`.
Nachgemessen: die Titel-Menge der 120 Fehlschläge ist in allen fünf Läufen identisch,
und es gibt über alle 600 Fehlschläge genau **einen** distinkten Fehlertext.
Variation existiert nur in Testtitel, Zeilennummer und Route.

**Ursache B — Linux-Baselines veraltet (56 rohe Fehlschläge).**
Alle vier Läufe vom 08.09. sind `toHaveScreenshot`-Abweichungen aus derselben
Testdatei `tests/visual/layout.spec.ts:33`. Zwei Erscheinungsformen:
Höhendifferenz (`Expected an image 1440px by 3760px, received 1440px by 3782px`)
und gleiche Abmessungen mit Pixelabweichung über der im Test gesetzten Schwelle
`maxDiffPixelRatio: 0.001`. Beide gehen auf dieselbe Ursache zurück (siehe unten)
und wurden **nicht** als zwei Ursachen gezählt.

## Sampling

Ziel war „höchstens 18 Fälle, höchstens 7 je Ursache". Bei genau zwei Ursachen ist
die Obergrenze damit **14** — und 14 Fälle wurden gezogen, 7 je Ursache.

Die fehlenden 4 wurden **bewusst nicht** aufgefüllt. Um auf 18 zu kommen, hätte man
Ursache B in „Höhendifferenz" und „Pixeldifferenz bei gleicher Größe" aufspalten
müssen. Das sind zwei Erscheinungsformen **einer** Ursache; sie zu trennen hätte die
Zahl gehoben und die Aussage verwässert.

Gezogen wurde nach maximaler Verschiedenheit der Evidenz, nicht zufällig:

**Ursache A (hist-001 … hist-007)** — die Qualitäts-Suite hat sechs distinkte
Assertion-Stellen (Zeilen 43, 68, 79, 89, 99, 105). Gezogen wurde **je eine pro
Stelle**, plus eine zweite an Zeile 79 mit anderem Viewport und anderer Route.
Verteilt über **alle fünf** Head-Commits, damit jeder Fall einen anderen
`diff.patch` trägt.

| Fall | Lauf | Zeile | Testtitel |
|---|---|---|---|
| hist-001 | 34139279743 | 43 | `/ — jedes Bild rendert mit echter Breite` |
| hist-002 | 34142330079 | 68 | `/es — keine Konsolenfehler` |
| hist-003 | 34144406466 | 79 | `/projekte — kein Querlauf (mobil)` |
| hist-004 | 34144629087 | 79 | `/en/services — kein Querlauf (tablet)` |
| hist-005 | 34147293024 | 89 | `/datenschutz — Seite bleibt unter 500 KB` |
| hist-006 | 34139279743 | 99 | `/unternehmen — genau eine H1` |
| hist-007 | 34142330079 | 105 | `kein Fremd-CDN, kein Tracker, kein jQuery` |

**Ursache B (hist-008 … hist-014)** — gezogen über sechs verschiedene Routen, beide
Viewports, beide Erscheinungsformen, alle vier Head-Commits, und über die ganze
Spannweite der Pixelverhältnisse (0,01 bis 0,17).

| Fall | Lauf | Route/Viewport | Evidenz |
|---|---|---|---|
| hist-008 | 34207139258 | `/es` desktop | 1440×3760 → 3782, 55043 px, 0,02 |
| hist-009 | 34207139258 | `/datenschutz` mobil | 390×3108 → 3179, 126760 px, 0,11 |
| hist-010 | 34207848044 | `/es/servicios` desktop | 1440×2820 → 2898, 459603 px, 0,12 |
| hist-011 | 34210053878 | `/unternehmen` desktop | gleiche Größe, 22726 px, 0,01 |
| hist-012 | 34210053878 | `/en/company` mobil | gleiche Größe, 4330 px, 0,01 |
| hist-013 | 34213646399 | `/unternehmen` desktop | 1440×3404 → 3439, 460404 px, 0,10 |
| hist-014 | 34213646399 | `/es/empresa` mobil | 390×4894 → 4986, 326032 px, 0,17 |

Zwei Fälle sind mit Absicht drin, weil sie Triage-Fallen sind:

* **hist-010** — der Head-Commit `c135d351` ändert **ausschließlich**
  `apps/kc-web/scripts/deploy-cf.mjs`, eine Datei, die in keiner gebauten Seite
  vorkommt. Der Fehlschlag ist byte-identisch zu dem aus dem Vorlauf. Wer den Diff
  unter Test für die Ursache hält, liegt hier nachweisbar falsch.
* **hist-011 / hist-013** — derselbe Test, dieselbe Ursache, zwei aufeinander
  folgende Commits, aber völlig verschiedene Beweislage (22726 px bei gleicher
  Größe gegen 460404 px mit Höhendifferenz).

## Labels und worauf sie ruhen

**Alle 14 Fälle: `KAPUTTER_TEST`, alle `gelabelt_von: "historie"`.**
Kein Fall ruht auf Modellurteil. Kein `claude-opus-5`-Label im Korpus.

**Ursache A** — der Fix ist `34b8d949e2b45e72a3f702e3a134a8094f505b4f` (PR #134):
er verschiebt in `.github/workflows/ci-test.yaml` den Schritt
`Install Playwright Browsers` **vor** den Schritt `Unit-Tests` und benennt den
Vorfall im Datei-Kommentar wörtlich: *„Solange dieser Schritt danach stand,
scheiterten am 07.09.2026 alle 120 kc-web-Pruefungen mit `browserType.launch:
Executable doesn't exist`."* Die Commit-Nachricht führt es als REPO-023. Geändert
wurde die CI-Umgebung — weder Produktcode noch Testcode. Nach `docs/fallformat.md`
ist eine fehlende Browser-Binary ausdrücklich `KAPUTTER_TEST`.

**Ursache B** — die Beweiskette ist dreiteilig und wurde vollständig nachgemessen:

1. `145bad4f629f50c34241e5be11ae334f61c7475a` (PR #136, 08.09.) legte die 34
   Linux-Aufnahmen an, aufgenommen auf einem CI-Runner vom damaligen `main`-Stand
   (`34b8d949`). Gegenprobe: `git diff 34b8d949..145bad4 -- apps/kc-web/` ist unter
   `src/` **leer** — die Baselines bilden den Branch-Ausgangsstand sauber ab.
2. Der PR-Branch änderte danach **absichtlich** Inhalt und erneuerte in denselben
   Commits **nur den win32-Satz** der Baselines:
   `811bc1dc` (KC-018, `src/content/es.ts`, 174 Korrekturen → nur `es-*-win32.png`),
   `8dcb8ab` (KC-016, `src/pages/datenschutz.astro`, 14 Zeilen),
   `da6194ac` (KC-020, H1 in de/en/es → nur `unternehmen-*` und `en-company-*-win32.png`),
   `4c6e53a1` (KC-021, dieselbe H1 erneut).
   Die CI läuft auf `ubuntu-latest` und sucht `*-visual-linux.png`.
3. Aufgelöst am 10.09. durch `5f3210fd6f6e946c0de34d636ab018fb267369f1`
   (*„test(KC-038): Linux-Baselines nachgezogen — sie waren aelter als der Umbau"*):
   **34 geänderte Dateien, ausschließlich PNG, 0 Zeilen Code.** Nachgemessen mit
   `git show --name-only 5f3210f | grep -v '\.png$'` → leer.

Ein Fix, der nur Baselines anfasst und den Lauf grün macht, ist per Definition
`KAPUTTER_TEST`.

## Artefakte je Fall

```
eval/cases/hist-NNN/
  fall.json         strukturierte Evidenz
  diff.patch        echter git-Diff, merge-base..head, gekürzt
  log_excerpt.txt   verbatimer, de-ANSI'ter Fehlschlag-Block aus dem CI-Log
```

* **Kein `report.json`.** In den Logs gibt es keinen Playwright-JSON-Report
  (`reporter: 'github'` in `playwright.config.ts`). Statt einen zu erfinden,
  referenziert `artefakte` den Log-Auszug als `{"ci_log": "log_excerpt.txt"}`.
* **Kein `trace.txt`, kein `screenshot.png`.** `trace: 'retain-on-failure'` ist zwar
  gesetzt, aber die Artefakte wurden nie hochgeladen und sind nicht mehr zu holen.
* **`dauer_ms` ist `null`.** Der `github`-Reporter druckt keine Laufzeit je Test.
  Der Schlüssel bleibt zur Formtreue stehen, der Wert ist ehrlich unbekannt.
* **`versuche` ist überall `[{"nr": 1, "status": "failed"}]`.** Nachgeprüft an allen
  neun Commits: `retries: 0` in `apps/kc-web/playwright.config.ts`. Es gab genau
  einen Versuch. Kein Fall erfindet einen Retry.

### diff.patch — was drin ist und was nicht

Erzeugt mit `git diff <merge-base(main, head)>..<head>`, gekürzt auf ~400 Zeilen an
der nächstgelegenen Dateigrenze, mit explizitem `[... truncated N lines ...]`-Marker,
der den vollständigen Befehl nennt. Alle Patches parsen mit `git apply --stat`.

Merge-Basis je Cluster: `fed35e0d` (07.09.), `34b8d949` (08.09.).

**Zwei Dateien sind aus jedem Patch per git-Pathspec ausgeschlossen:**
`apps/kc-web/BLOCKERS.md` und `apps/kc-web/DECISIONS.md`. Beide nennen einen
Referenzkunden namentlich, dessen schriftliche Freigabe zu dem Zeitpunkt noch
ausstand. Das ist eine deklarierte Schwärzung, keine Fälschung: jeder Patch trägt sie
im Fußzeilen-Marker. Sonst wurde nichts verändert. Nebeneffekt: das 400-Zeilen-Fenster
reicht dadurch bis `playwright.config.ts` und `package.json` — die Schwärzung hat den
Informationsgehalt erhöht, nicht gesenkt.

Geprüft wurde der gesamte ausgelieferte Inhalt auf Token-Muster (`ghp_`, `sk-`,
`AKIA`, `xox*`, PEM-Header), `***`-maskierte Zeilen, E-Mail-Adressen und
Kundennamen. Treffer: keine. Die verbleibenden Vorkommen von „Referenzkunden" sind
Mengenangaben („dreizehn Referenzkunden"), keine Namen.

## Schwächen — bitte mitlesen

1. **Eine einzige Klasse.** Alle 14 Fälle sind `KAPUTTER_TEST`. Es gibt **null**
   `PRODUKTFEHLER` und **null** `FLAKE`. Ein Klassifikator, der blind
   „KAPUTTER_TEST" rät, erreicht auf diesem Teilkorpus 100 %. Die `hist-*`-Fälle
   können für sich genommen **keine** Precision/Recall-Aussage tragen; sie sind nur
   im Verbund mit den synthetischen Fällen sinnvoll, und die Klassenverteilung des
   Gesamtkorpus muss im README stehen.
2. **Nur zwei Ursachen und eine App.** 656 rohe Fehlschläge kollabieren auf zwei
   Ursachen, beide aus `apps/kc-web`, beide Playwright. Das ist kein Querschnitt
   durch CI-Fehlschläge, sondern zwei gut dokumentierte Vorfälle.
3. **Kein FLAKE, obwohl zunächst danach aussah.** Zwischen Lauf 34210053878 und
   34213646399 ändern sich die Pixelzahlen desselben Tests (22726 → 460404). Das
   sah nach Nichtdeterminismus aus, ist aber durch verschiedene Head-Commits
   (`da6194ac` vs. `4c6e53a1`, beide ändern dieselbe H1) vollständig erklärt.
   Es wurde **nicht** als FLAKE gelabelt. Ohne Rerun desselben Commits ist Flakiness
   aus diesen Daten nicht belegbar.
4. **Der Diff unter Test enthält die Ursache A nie.** Bei den sieben
   Browser-Binary-Fällen liegt die Ursache im Workflow, der zum Zeitpunkt des Laufs
   gar nicht im Diff stand. Ein Agent kann diese Fälle nur über den Fehlertext
   lösen, nicht über den Diff. Das ist realistisch, aber es macht `diff.patch` dort
   zu Kontext statt zu Evidenz.
5. **Die CI testete den PR-Merge-Commit, nicht den Head-Commit.** Die Logs zeigen
   `Merge <head> into <base>` gegen `refs/remotes/pull/<n>/merge`. `kontext.commit`
   trägt den Head-Commit (das, was gepusht wurde); die CI-Basis wich davon ab —
   für PR #135 war sie `145bad4` bzw. `9f571b3`, nicht die Merge-Basis `34b8d949`.
   Gegengeprüft: zwischen `145bad4` und `9f571b3` hat `main` nichts unter
   `apps/kc-web/` angefasst, die Labels sind davon also nicht betroffen.
6. **Zwei Testtitel kommen doppelt vor.** hist-011 und hist-013 tragen denselben
   `test_titel` (verschiedene Läufe/Commits). Wer über Titel dedupliziert statt über
   `id`, zählt hier falsch.
