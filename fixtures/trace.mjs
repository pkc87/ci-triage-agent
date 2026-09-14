// Turn a Playwright trace.zip into a readable action log.
//
// Traces are zip archives whose *.trace member is newline-delimited JSON. We
// only need the action events, so this reads the archive with node:zlib instead
// of pulling in a zip dependency.

import { readFileSync } from 'node:fs';
import { inflateRawSync } from 'node:zlib';

const EOCD_SIGNATURE = 0x06054b50;
const CENTRAL_SIGNATURE = 0x02014b50;

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
      // A truncated trailing line means the run was killed; skip it.
    }
  }
  return events;
}

function short(value, limit = 160) {
  const text = String(value).replace(/\s+/g, ' ').trim();
  return text.length > limit ? `${text.slice(0, limit - 1)}…` : text;
}

function describeParams(params = {}) {
  const interesting = ['url', 'selector', 'value', 'text', 'expression', 'timeout', 'key'];
  const parts = [];
  for (const key of interesting) {
    if (params[key] !== undefined && params[key] !== null && params[key] !== '') {
      parts.push(`${key}=${short(params[key], 70)}`);
    }
  }
  return parts.join(' ');
}

/**
 * Build a compact action log: one line per API call with duration and error,
 * followed by the console and page errors the trace recorded.
 */
export function traceToText(zipPath) {
  const entries = readZip(zipPath);
  const traceNames = [...entries.keys()].filter((name) => name.endsWith('.trace'));
  if (traceNames.length === 0) throw new Error(`no .trace member in ${zipPath}`);

  const events = traceNames.flatMap((name) => parseEvents(entries.get(name).toString('utf8')));

  const calls = new Map();
  const order = [];
  const logs = [];

  for (const event of events) {
    if (event.type === 'before') {
      calls.set(event.callId, {
        title: event.title ?? event.apiName ?? event.method,
        params: event.params,
        start: event.startTime,
      });
      order.push(event.callId);
    } else if (event.type === 'after') {
      const call = calls.get(event.callId);
      if (call) {
        call.end = event.endTime;
        call.error = event.error?.error?.message ?? event.error?.message;
      }
    } else if (event.type === 'log') {
      const call = calls.get(event.callId);
      if (call) (call.log ??= []).push(event.message);
    } else if (event.type === 'console') {
      const text = (event.args ?? []).map((arg) => arg.preview ?? arg.value ?? '').join(' ');
      logs.push(`console.${event.messageType ?? 'log'}: ${short(text)}`);
    } else if (event.type === 'event' && event.method === 'pageError') {
      logs.push(`pageerror: ${short(event.params?.error?.error?.message ?? '')}`);
    }
  }

  const lines = [];
  let step = 0;
  for (const callId of order) {
    const call = calls.get(callId);
    if (!call) continue;
    step += 1;
    const duration = call.end && call.start ? `${Math.round(call.end - call.start)}ms` : '-';
    const params = describeParams(call.params);
    lines.push(`${String(step).padStart(3, ' ')}. ${call.title}${params ? ` [${params}]` : ''} (${duration})`);
    if (call.error) {
      lines.push(`     ERROR: ${short(call.error, 400)}`);
      for (const message of (call.log ?? []).slice(-6)) {
        lines.push(`     log: ${short(message, 200)}`);
      }
    }
  }

  if (logs.length > 0) {
    lines.push('', '--- page output ---', ...logs.slice(0, 40));
  }

  return `${lines.join('\n')}\n`;
}

if (process.argv[1] && import.meta.url.endsWith(process.argv[1].replace(/\\/g, '/').split('/').pop())) {
  const target = process.argv[2];
  if (target) process.stdout.write(traceToText(target));
}
