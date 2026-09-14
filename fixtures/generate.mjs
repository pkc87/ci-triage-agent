#!/usr/bin/env node
// Regenerate the synthetic half of the triage corpus.
//
//   node fixtures/generate.mjs                 full corpus (wipes eval/cases/syn-*)
//   node fixtures/generate.mjs --only mut-03   run one mutation, write nothing
//   node fixtures/generate.mjs --only mut-03,mut-06 --runs 8
//   node fixtures/generate.mjs --only mut-24 --write --anhaengen
//
// --anhaengen ("append") extends the corpus that is already on disk instead of
// rebuilding it: nothing is wiped, the case counter continues after the highest
// syn-NNN present, and the new ground-truth lines are appended. That is how a
// mutation added later gets its cases without renumbering every case that was
// published before it. A plain run still rebuilds the whole synthetic half.
//
// For every mutation: apply it, run the real Playwright suite, keep the real
// JSON report, cut one case per failing test, revert. Nothing here is written
// by hand -- if a mutation does not break anything, it produces no case.

import { spawnSync } from 'node:child_process';
import {
  appendFileSync,
  copyFileSync,
  existsSync,
  lstatSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  rmdirSync,
  unlinkSync,
  writeFileSync,
} from 'node:fs';
import { dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { stripAnsi, traceToText } from './trace.mjs';

const FIXTURES = dirname(fileURLToPath(import.meta.url));
const REPO = resolve(FIXTURES, '..');
const MUTATIONS_DIR = join(FIXTURES, 'mutations');
const RUNS_DIR = join(FIXTURES, 'runs');
const CASES_DIR = join(REPO, 'eval', 'cases');
const GROUND_TRUTH = join(REPO, 'eval', 'ground_truth_syn.jsonl');
const PLAYWRIGHT_CLI = join(FIXTURES, 'node_modules', '@playwright', 'test', 'cli.js');

// The corpus is public: no absolute path from this machine belongs in it.
const SCRUB_TARGET = '/work/ci-triage-agent';

const SCRUBBED_PATH = new RegExp(`${SCRUB_TARGET}[\\\\/][^\\s"'\`)\\]]*`, 'g');

function scrub(text) {
  if (text === undefined || text === null) return text;
  return stripAnsi(String(text))
    .split(REPO.replace(/\\/g, '/'))
    .join(SCRUB_TARGET)
    .split(REPO)
    .join(SCRUB_TARGET)
    .split(REPO.replace(/\\/g, '\\\\'))
    .join(SCRUB_TARGET)
    .replace(SCRUBBED_PATH, (match) => match.replace(/\\/g, '/'));
}

/**
 * Delete a file or directory tree.
 *
 * Not fs.rmSync: some sandboxed environments neuter it into a silent no-op,
 * which would leave a mutation's new spec file lying around and poison every
 * later run. unlink + rmdir either work or throw.
 */
function entfernen(ziel) {
  if (!existsSync(ziel)) return;
  if (lstatSync(ziel).isDirectory()) {
    for (const name of readdirSync(ziel)) entfernen(join(ziel, name));
    rmdirSync(ziel);
  } else {
    unlinkSync(ziel);
  }
}

function scrubDeep(value) {
  if (typeof value === 'string') return scrub(value);
  if (Array.isArray(value)) return value.map(scrubDeep);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).map(([key, inner]) => [key, scrubDeep(inner)]));
  }
  return value;
}

function parseArgs(argv) {
  const args = { only: null, runs: null, probe: false, anhaengen: false };
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === '--only') {
      args.only = argv[i + 1].split(',').map((value) => value.trim());
      args.probe = true;
      i += 1;
    } else if (argv[i] === '--runs') {
      args.runs = Number(argv[i + 1]);
      i += 1;
    } else if (argv[i] === '--write') {
      args.probe = false;
    } else if (argv[i] === '--anhaengen') {
      args.anhaengen = true;
    }
  }
  return args;
}

/** Highest syn-NNN already on disk, so an appending run continues after it. */
function hoechsteFallnummer() {
  if (!existsSync(CASES_DIR)) return 0;
  let hoechste = 0;
  for (const name of readdirSync(CASES_DIR)) {
    const treffer = /^syn-(\d+)$/.exec(name);
    if (treffer) hoechste = Math.max(hoechste, Number(treffer[1]));
  }
  return hoechste;
}

function loadMutations(only) {
  return readdirSync(MUTATIONS_DIR)
    .filter((name) => existsSync(join(MUTATIONS_DIR, name, 'mutation.json')))
    .sort()
    .map((name) => ({
      ...JSON.parse(readFileSync(join(MUTATIONS_DIR, name, 'mutation.json'), 'utf8')),
      _pfad: join(MUTATIONS_DIR, name, 'mutation.json'),
    }))
    .filter((mutation) => !only || only.includes(mutation.id));
}

function applyMutation(mutation) {
  const originals = [];
  for (const change of mutation.aenderungen) {
    const target = join(FIXTURES, change.datei);
    if (change.inhalt !== undefined) {
      // A file a mutation creates must never survive into the next run: it
      // would race the base suite and every later mutation would inherit it.
      if (existsSync(target)) {
        process.stderr.write(`  warning: ${change.datei} was left behind, removing it first\n`);
        entfernen(target);
      }
      originals.push({ datei: change.datei, target, vorher: null });
      mkdirSync(dirname(target), { recursive: true });
      writeFileSync(target, change.inhalt, 'utf8');
      continue;
    }
    const before = readFileSync(target, 'utf8');
    const hits = before.split(change.suchen).length - 1;
    if (hits !== 1) {
      throw new Error(`${mutation.id}: anchor matched ${hits}x in ${change.datei}`);
    }
    originals.push({ datei: change.datei, target, vorher: before });
    writeFileSync(target, before.replace(change.suchen, change.ersetzen), 'utf8');
  }
  return originals;
}

function revertMutation(originals) {
  for (const entry of originals) {
    if (entry.vorher === null) {
      if (existsSync(entry.target)) entfernen(entry.target);
    } else {
      writeFileSync(entry.target, entry.vorher, 'utf8');
    }
  }
}

/** Unified diff of the mutation, as it would show up in a merge request. */
function buildDiff(mutation, originals) {
  const tmp = join(RUNS_DIR, '.diff');
  entfernen(tmp);
  const chunks = [];

  for (const entry of originals) {
    const repoPath = `fixtures/${entry.datei}`.replace(/\\/g, '/');
    const after = readFileSync(entry.target, 'utf8');

    if (entry.vorher === null) {
      const lines = after.split('\n');
      if (lines.at(-1) === '') lines.pop();
      chunks.push(
        [
          `diff --git a/${repoPath} b/${repoPath}`,
          'new file mode 100644',
          '--- /dev/null',
          `+++ b/${repoPath}`,
          `@@ -0,0 +1,${lines.length} @@`,
          ...lines.map((line) => `+${line}`),
          '',
        ].join('\n'),
      );
      continue;
    }

    const before = join(tmp, 'a', repoPath);
    const now = join(tmp, 'b', repoPath);
    mkdirSync(dirname(before), { recursive: true });
    mkdirSync(dirname(now), { recursive: true });
    writeFileSync(before, entry.vorher, 'utf8');
    writeFileSync(now, after, 'utf8');

    const result = spawnSync(
      'git',
      ['diff', '--no-index', '--no-prefix', '-U3', '--', `a/${repoPath}`, `b/${repoPath}`],
      { cwd: tmp, encoding: 'utf8' },
    );
    if (!result.stdout) throw new Error(`${mutation.id}: empty diff for ${repoPath}`);
    chunks.push(result.stdout);
  }

  entfernen(tmp);
  return chunks.join('');
}

function runSuite(mutation, index) {
  const outDir = join(RUNS_DIR, mutation.id, String(index));
  entfernen(outDir);
  mkdirSync(outDir, { recursive: true });
  const reportPath = join(outDir, 'report.json');

  const started = Date.now();
  const result = spawnSync(
    process.execPath,
    [PLAYWRIGHT_CLI, 'test', '--output', join(outDir, 'artifacts')],
    {
      cwd: FIXTURES,
      encoding: 'utf8',
      maxBuffer: 64 * 1024 * 1024,
      env: { ...process.env, PW_JSON_REPORT: reportPath, FORCE_COLOR: '0' },
    },
  );

  const report = existsSync(reportPath) ? JSON.parse(readFileSync(reportPath, 'utf8')) : null;
  return {
    index,
    outDir,
    report,
    dauer_ms: Date.now() - started,
    exitCode: result.status,
    stderr: (result.stderr ?? '').slice(-2000),
  };
}

function* iterSpecs(suite) {
  for (const spec of suite.specs ?? []) yield spec;
  for (const child of suite.suites ?? []) yield* iterSpecs(child);
}

const FAILED = new Set(['failed', 'timedOut', 'interrupted']);

/** Every test with at least one failing attempt, in report order. */
function collectFailures(report) {
  if (!report) return [];
  const failures = [];
  for (const suite of report.suites ?? []) {
    for (const spec of iterSpecs(suite)) {
      for (const test of spec.tests ?? []) {
        const failing = (test.results ?? []).filter((result) => FAILED.has(result.status));
        if (failing.length > 0) failures.push({ suite, spec, test, failing });
      }
    }
  }
  return failures;
}

function sliceReport(report, suite, spec, test) {
  return scrubDeep({
    config: report.config,
    suites: [
      {
        title: suite.title,
        file: suite.file,
        line: suite.line,
        column: suite.column,
        specs: [{ ...spec, tests: [test] }],
      },
    ],
    errors: report.errors ?? [],
    stats: report.stats,
  });
}

function writeCase({ caseId, mutation, diff, run, failure, gitCommit }) {
  const dir = join(CASES_DIR, caseId);
  entfernen(dir);
  mkdirSync(dir, { recursive: true });

  const { suite, spec, test, failing } = failure;
  const first = failing[0];
  const artefakte = { diff: 'diff.patch' };

  const traceAttachment = (first.attachments ?? []).find((item) => item.name === 'trace');
  if (traceAttachment?.path && existsSync(traceAttachment.path)) {
    try {
      writeFileSync(join(dir, 'trace.txt'), scrub(traceToText(traceAttachment.path)), 'utf8');
      artefakte.trace = 'trace.txt';
    } catch (error) {
      process.stderr.write(`  trace extraction failed for ${caseId}: ${error.message}\n`);
    }
  }

  const attachments = first.attachments ?? [];
  const shot =
    attachments.find((item) => item.name.endsWith('-diff.png')) ??
    attachments.find((item) => item.name === 'screenshot');
  if (shot?.path && existsSync(shot.path)) {
    copyFileSync(shot.path, join(dir, 'screenshot.png'));
    artefakte.screenshot = 'screenshot.png';
  }

  writeFileSync(join(dir, 'diff.patch'), diff, 'utf8');
  writeFileSync(
    join(dir, 'report.json'),
    `${JSON.stringify(sliceReport(run.report, suite, spec, test), null, 2)}\n`,
    'utf8',
  );

  // The report's rootDir is the common root of the spec files, so rebuild the
  // path the way a reader of the repo would write it: tests/<spec>.
  const specPath = relative(FIXTURES, resolve(run.report.config.rootDir, spec.file)).replace(/\\/g, '/');
  const stack = [first.error?.stack ?? first.errors?.[0]?.stack, first.error?.snippet]
    .filter(Boolean)
    .join('\n\n');

  const fall = {
    id: caseId,
    quelle: 'synthetisch',
    repo: 'fixtures/shop',
    test_titel: spec.title,
    test_datei: specPath,
    test_zeile: spec.line,
    fehlermeldung: scrub(first.error?.message ?? first.errors?.[0]?.message ?? ''),
    stack: scrub(stack),
    dauer_ms: first.duration,
    versuche: (test.results ?? []).map((result) => ({ nr: result.retry + 1, status: result.status })),
    artefakte,
    kontext: {
      branch: `mr/${mutation.id}`,
      commit: gitCommit,
      ci_lauf: 'lokal (fixtures/generate.mjs)',
    },
  };
  writeFileSync(join(dir, 'fall.json'), `${JSON.stringify(fall, null, 2)}\n`, 'utf8');
  return fall;
}

function gitShortHead() {
  const result = spawnSync('git', ['rev-parse', '--short', 'HEAD'], { cwd: REPO, encoding: 'utf8' });
  return (result.stdout ?? '').trim() || 'unknown';
}

function wipeSynthetic() {
  if (existsSync(CASES_DIR)) {
    for (const name of readdirSync(CASES_DIR)) {
      if (name.startsWith('syn-')) entfernen(join(CASES_DIR, name));
    }
  }
  mkdirSync(CASES_DIR, { recursive: true });
  if (existsSync(GROUND_TRUTH)) entfernen(GROUND_TRUTH);
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const mutations = loadMutations(args.only);
  if (mutations.length === 0) throw new Error('no mutations selected');

  // Any spec a mutation creates belongs to that mutation only. If a previous
  // run was interrupted, one can still be on disk -- clear it before measuring.
  for (const mutation of loadMutations(null)) {
    for (const change of mutation.aenderungen) {
      if (change.inhalt === undefined) continue;
      const target = join(FIXTURES, change.datei);
      if (existsSync(target)) {
        process.stdout.write(`removing leftover ${change.datei} from ${mutation.id}\n`);
        entfernen(target);
      }
    }
  }

  if (args.anhaengen && !args.only) {
    throw new Error('--anhaengen only makes sense together with --only');
  }
  if (!args.probe && !args.anhaengen) wipeSynthetic();
  mkdirSync(RUNS_DIR, { recursive: true });

  const gitCommit = gitShortHead();
  const groundTruth = [];
  let counter = args.anhaengen ? hoechsteFallnummer() : 0;

  for (const mutation of mutations) {
    const laeufe = args.runs ?? mutation.laeufe ?? 1;
    process.stdout.write(`\n=== ${mutation.id} [${mutation.klasse}] ${laeufe} run(s)\n`);

    let originals = [];
    let diff = '';
    const runs = [];
    try {
      originals = applyMutation(mutation);
      diff = buildDiff(mutation, originals);
      for (let i = 1; i <= laeufe; i += 1) {
        const run = runSuite(mutation, i);
        const failures = collectFailures(run.report);
        run.failures = failures;
        runs.push(run);
        process.stdout.write(
          `  run ${i}: exit=${run.exitCode} failing tests=${failures.length} ` +
            `(${failures.map((f) => f.spec.title).join(' | ') || 'none'})\n`,
        );
      }
    } finally {
      revertMutation(originals);
    }

    const attempts = runs.flatMap((run) =>
      (run.failures ?? []).flatMap((failure) => failure.test.results.map((r) => r.status)),
    );
    const beobachtet = {
      laeufe: runs.length,
      fehlschlaege: runs.filter((run) => (run.failures ?? []).length > 0).length,
      versuche_gesamt: attempts.length,
      versuche_fehlgeschlagen: attempts.filter((status) => FAILED.has(status)).length,
    };
    const { _pfad, ...gespeichert } = mutation;
    writeFileSync(_pfad, `${JSON.stringify({ ...gespeichert, beobachtet }, null, 2)}\n`, 'utf8');

    const caseRun = runs.find((run) => (run.failures ?? []).length > 0);
    if (!caseRun) {
      process.stdout.write(`  !! ${mutation.id} produced no failure in ${runs.length} run(s)\n`);
      continue;
    }
    if (args.probe) continue;

    for (const failure of caseRun.failures.slice(0, mutation.max_faelle ?? 99)) {
      counter += 1;
      const caseId = `syn-${String(counter).padStart(3, '0')}`;
      writeCase({ caseId, mutation, diff, run: caseRun, failure, gitCommit });

      const label = mutation.klasse;
      const rate =
        label === 'FLAKE'
          ? ` (observed: ${beobachtet.fehlschlaege}/${beobachtet.laeufe} runs with a failing attempt, ` +
            `${beobachtet.versuche_fehlgeschlagen}/${beobachtet.versuche_gesamt} attempts failed)`
          : '';
      groundTruth.push({
        id: caseId,
        label,
        quelle: 'synthetisch',
        gelabelt_von: 'konstruktion',
        begruendung_label: `${mutation.id}: ${mutation.begruendung ?? mutation.beschreibung}${rate}`,
        mutation: mutation.id,
      });
      process.stdout.write(`  -> ${caseId}  ${failure.spec.title}\n`);
    }
  }

  if (!args.probe) {
    const zeilen = groundTruth.map((line) => JSON.stringify(line)).join('\n');
    if (!args.anhaengen) writeFileSync(GROUND_TRUTH, `${zeilen}\n`, 'utf8');
    else if (zeilen) appendFileSync(GROUND_TRUTH, `${zeilen}\n`, 'utf8');
    const perClass = groundTruth.reduce((acc, line) => ({ ...acc, [line.label]: (acc[line.label] ?? 0) + 1 }), {});
    process.stdout.write(`\n${groundTruth.length} cases: ${JSON.stringify(perClass)}\n`);
  }
}

main();
