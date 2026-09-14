// Turn a Playwright trace.zip into a readable action log.
//
// A trace is a zip archive whose *.trace members are newline-delimited JSON.
// `test.trace` carries the test-runner view (steps, expects, hook boundaries),
// which is what a human reads first, so that is what this extracts. No zip
// dependency: node:zlib can inflate the members directly.

import { readFileSync } from 'node:fs';
import { inflateRawSync } from 'node:zlib';

const EOCD_SIGNATURE = 0x06054b50;
const CENTRAL_SIGNATURE = 0x02014b50;

// CSI and OSC escape sequences: Playwright colours its error text even in a file.
const ANSI = new RegExp('[\\u001B\\u009B][[\\]()#;?]*(?:(?:[a-zA-Z\\d]*(?:;[-a-zA-Z\\d/#&.:=?%@~_]*)*)?\\u0007|(?:\\d{1,4}(?:;\\d{0,4})*)?[\\dA-PR-TZcf-nq-uy=><~])', 'g');

export function stripAnsi(text) {
  return String(text ?? '').replace(ANSI, '');
}

/** Read a zip archive into a Map of entry name -> Buffer. */
export function readZip(path) {
  const buffer = readFileSync(path);
  const entries = new Map();

  let eocd = -1;
  for (let i = buffer.length - 22; i >= 0; i -= 1) {
    if (buffer.readUInt32LE(i) === EOCD_SIGNATURE) {
      eocd = i;
      break;
    }
  }
  if (eocd < 0) throw new Error(`not a zip archive: ${path}`);

  const entryCount = buffer.readUInt16LE(eocd + 10);
  let offset = buffer.readUInt32LE(eocd + 16);

  for (let i = 0; i < entryCount; i += 1) {
    if (buffer.readUInt32LE(offset) !== CENTRAL_SIGNATURE) break;
    const method = buffer.readUInt16LE(offset + 10);
    const compressedSize = buffer.readUInt32LE(offset + 20);
    const nameLength = buffer.readUInt16LE(offset + 28);
    const extraLength = buffer.readUInt16LE(offset + 30);
    const commentLength = buffer.readUInt16LE(offset + 32);
    const localOffset = buffer.readUInt32LE(offset + 42);
    const name = buffer.toString('utf8', offset + 46, offset + 46 + nameLength);

    const localNameLength = buffer.readUInt16LE(localOffset + 26);
    const localExtraLength = buffer.readUInt16LE(localOffset + 28);
    const dataStart = localOffset + 30 + localNameLength + localExtraLength;
    const raw = buffer.subarray(dataStart, dataStart + compressedSize);

    entries.set(name, method === 0 ? Buffer.from(raw) : inflateRawSync(raw));
    offset += 46 + nameLength + extraLength + commentLength;
  }

  return entries;
}

function parseEvents(text) {
  const events = [];
  for (const line of text.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    try {
      events.push(JSON.parse(trimmed));
    } catch {
      // A truncated trailing line means the run was killed mid-write; skip it.
    }
  }
  return events;
}

function shorten(value, limit) {
  const text = stripAnsi(value).replace(/\s+/g, ' ').trim();
  return text.length > limit ? `${text.slice(0, limit - 1)}...` : text;
}

const INTERESTING_PARAMS = ['url', 'expected', 'selector', 'value', 'text', 'key', 'timeout'];

function describeParams(params = {}) {
  const parts = [];
  for (const key of INTERESTING_PARAMS) {
    const value = params[key];
    if (value === undefined || value === null || value === '' || value === '0') continue;
    parts.push(`${key}=${shorten(value, 90)}`);
  }
  return parts.join(' ');
}

/** Build a compact, human-readable action log for one trace archive. */
export function traceToText(zipPath) {
  const entries = readZip(zipPath);
  const preferred = entries.has('test.trace')
    ? ['test.trace']
    : [...entries.keys()].filter((name) => name.endsWith('.trace'));
  if (preferred.length === 0) throw new Error(`no .trace member in ${zipPath}`);

  const events = preferred.flatMap((name) => parseEvents(entries.get(name).toString('utf8')));

  const calls = new Map();
  const order = [];
  const topLevelErrors = [];

  for (const event of events) {
    if (event.type === 'before') {
      calls.set(event.callId, {
        title: event.title ?? event.method,
        params: event.params,
        parentId: event.parentId,
        start: event.startTime,
      });
      order.push(event.callId);
    } else if (event.type === 'after') {
      const call = calls.get(event.callId);
      if (!call) continue;
      call.end = event.endTime;
      call.error = event.error?.message ?? event.error?.error?.message;
    } else if (event.type === 'error') {
      topLevelErrors.push(event.message ?? '');
    }
  }

  const depthOf = (callId) => {
    let depth = 0;
    let current = calls.get(callId);
    while (current?.parentId && calls.has(current.parentId)) {
      depth += 1;
      current = calls.get(current.parentId);
    }
    return depth;
  };

  const lines = [];
  for (const callId of order) {
    const call = calls.get(callId);
    if (!call) continue;
    // Fixture set-up and tear-down is noise for triage; the steps are not.
    if (/^Fixture "/.test(call.title)) continue;

    const indent = '  '.repeat(Math.min(depthOf(callId), 3));
    const duration = Number.isFinite(call.end - call.start) ? `${Math.round(call.end - call.start)}ms` : '-';
    const params = describeParams(call.params);
    lines.push(`${indent}${call.title}${params ? ` [${params}]` : ''}  (${duration})`);

    if (call.error) {
      for (const errorLine of stripAnsi(call.error).split('\n').slice(0, 30)) {
        lines.push(`${indent}  ! ${errorLine}`);
      }
    }
  }

  if (topLevelErrors.length > 0) {
    lines.push('', '--- test errors ---');
    for (const message of topLevelErrors) {
      lines.push(...stripAnsi(message).split('\n').slice(0, 40));
    }
  }

  return `${lines.join('\n')}\n`;
}

if (process.argv[2]) {
  process.stdout.write(traceToText(process.argv[2]));
}
