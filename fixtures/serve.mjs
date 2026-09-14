// Minimal static server for fixtures/shop plus one stateful endpoint.
// No dependencies: node:http, node:fs, node:path, node:url only.

import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { extname, join, normalize, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(fileURLToPath(new URL('./shop', import.meta.url)));
const PORT = Number(process.env.SHOP_PORT ?? 4173);

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
};

// Deliberately process-wide: a single saved cart shared by every browser that
// talks to this server. The storefront calls it "Save cart".
let savedCart = { lines: [] };

function sendJson(res, status, payload) {
  const body = JSON.stringify(payload);
  res.writeHead(status, {
    'content-type': 'application/json; charset=utf-8',
    'content-length': Buffer.byteLength(body),
    'cache-control': 'no-store',
  });
  res.end(body);
}

async function readBody(req) {
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  return Buffer.concat(chunks).toString('utf8');
}

const server = createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host ?? '127.0.0.1'}`);

  if (url.pathname === '/api/saved-cart') {
    if (req.method === 'GET') {
      sendJson(res, 200, savedCart);
      return;
    }
    if (req.method === 'PUT') {
      try {
        const parsed = JSON.parse((await readBody(req)) || '{}');
        savedCart = { lines: Array.isArray(parsed.lines) ? parsed.lines : [] };
        sendJson(res, 200, savedCart);
      } catch {
        sendJson(res, 400, { error: 'invalid json' });
      }
      return;
    }
    sendJson(res, 405, { error: 'method not allowed' });
    return;
  }

  if (req.method !== 'GET' && req.method !== 'HEAD') {
    sendJson(res, 405, { error: 'method not allowed' });
    return;
  }

  const requested = url.pathname === '/' ? '/index.html' : url.pathname;
  const relative = normalize(decodeURIComponent(requested)).replace(/^([/\\])+/, '');
  const filePath = join(ROOT, relative);

  if (!filePath.startsWith(ROOT)) {
    res.writeHead(403, { 'content-type': 'text/plain; charset=utf-8' });
    res.end('forbidden');
    return;
  }

  try {
    const data = await readFile(filePath);
    res.writeHead(200, {
      'content-type': TYPES[extname(filePath).toLowerCase()] ?? 'application/octet-stream',
      'content-length': data.length,
      'cache-control': 'no-store',
    });
    res.end(req.method === 'HEAD' ? undefined : data);
  } catch {
    res.writeHead(404, { 'content-type': 'text/plain; charset=utf-8' });
    res.end('not found');
  }
});

server.listen(PORT, '127.0.0.1', () => {
  process.stdout.write(`shop fixture listening on http://127.0.0.1:${PORT}\n`);
});
