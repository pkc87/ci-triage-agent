// Scratch probe, deleted again once the numbers are in. Not a test: it lives
// outside testDir, so the Playwright suite never picks it up.
//
//   node fixtures/probe-tmp.mjs
//
// Answers two questions before a mutation is written:
//   1. how much page time passes between page.clock.install() and the moment
//      the shop stamps the order date (decides where the midnight boundary has
//      to sit for the rollover to be a coin flip), and
//   2. at which viewport width the shuffled recommendations strip sometimes
//      fits on one row and sometimes wraps.

import { spawn } from 'node:child_process';
import { dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

import { chromium } from '@playwright/test';

const FIXTURES = dirname(fileURLToPath(import.meta.url));
const PORT = 4199;
const BASE = `http://127.0.0.1:${PORT}`;

const server = spawn(process.execPath, ['serve.mjs'], {
  cwd: FIXTURES,
  env: { ...process.env, SHOP_PORT: String(PORT) },
  stdio: 'ignore',
});

async function warten(ms) {
  await new Promise((resolve) => setTimeout(resolve, ms));
}

async function serverBereit() {
  for (let i = 0; i < 40; i += 1) {
    try {
      const antwort = await fetch(BASE + '/index.html');
      if (antwort.ok) return true;
    } catch {
      /* not up yet */
    }
    await warten(150);
  }
  return false;
}

async function uhrProbe(browser) {
  const BASIS = '2026-03-14T12:00:00.000Z';
  console.log('\n--- clock: page time from install() to the printed order date');
  for (let i = 1; i <= 8; i += 1) {
    const page = await browser.newPage({ timezoneId: 'UTC' });
    try {
      await page.clock.install({ time: new Date(BASIS) });
      await page.clock.resume();
      await page.goto(BASE + '/');
      await page.getByTestId('add-p1').click();
      await page.getByTestId('name').fill('Dana Fisher');
      await page.getByTestId('email').fill('dana@example.com');
      await page.getByTestId('zip').fill('94110');
      await page.getByTestId('place-order').click();
      const text = await page.getByTestId('order-confirmation').textContent();
      const jetzt = await page.evaluate(() => Date.now());
      console.log(
        `  run ${i}: page clock advanced ${jetzt - Date.parse(BASIS)} ms, confirmation: ${text}`,
      );
    } catch (error) {
      console.log(`  run ${i}: FAILED ${error.message.split('\n')[0]}`);
    }
    await page.close();
  }
}

async function layoutProbe(browser) {
  console.log('\n--- layout: does the recommendations strip wrap?');
  for (const width of [400, 420, 440, 460, 480, 520]) {
    const page = await browser.newPage({ viewport: { width, height: 800 } });
    const zaehler = { eineZeile: 0, umbruch: 0 };
    const breiten = new Map();
    for (let i = 0; i < 16; i += 1) {
      await page.goto(BASE + '/');
      const messung = await page.evaluate(() => {
        const items = [...document.querySelectorAll('[data-testid="rec-item"]')];
        const kaesten = items.map((item) => item.getBoundingClientRect());
        return {
          namen: items.map((item) => item.textContent.trim()),
          breiten: kaesten.map((kasten) => Math.round(kasten.width)),
          eineZeile: kaesten.every((kasten) => Math.round(kasten.y) === Math.round(kaesten[0].y)),
          container: Math.round(
            document.querySelector('[data-testid="recommendations"]').getBoundingClientRect().width,
          ),
        };
      });
      for (const [index, name] of messung.namen.entries()) {
        breiten.set(name, messung.breiten[index]);
      }
      if (messung.eineZeile) zaehler.eineZeile += 1;
      else zaehler.umbruch += 1;
      if (i === 0) console.log(`  width ${width}: container ${messung.container}px`);
    }
    console.log(
      `  width ${width}: one row ${zaehler.eineZeile}/16, wrapped ${zaehler.umbruch}/16  ` +
        `items ${[...breiten.entries()].map(([n, b]) => `${n}=${b}`).join(' ')}`,
    );
    await page.close();
  }
}

async function textProbe(browser) {
  console.log('\n--- text locator: how often does "Burr Grinder" resolve twice?');
  const page = await browser.newPage();
  let doppelt = 0;
  for (let i = 0; i < 16; i += 1) {
    await page.goto(BASE + '/');
    const treffer = await page.getByText('Burr Grinder').count();
    if (treffer > 1) doppelt += 1;
  }
  console.log(`  two matches in ${doppelt}/16 loads`);
  await page.close();
}

async function main() {
  if (!(await serverBereit())) throw new Error('fixture server did not come up');
  const browser = await chromium.launch();
  try {
    await uhrProbe(browser);
    await layoutProbe(browser);
    await textProbe(browser);
  } finally {
    await browser.close();
    server.kill();
  }
}

await main();
