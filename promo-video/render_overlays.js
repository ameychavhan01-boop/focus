// Renders each overlay (caption, hook, CTA...) from overlays.json into a transparent PNG.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
(async () => {
  const [, , jsonPath, outDir] = process.argv;
  const items = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  const css = fs.readFileSync(path.join(__dirname, 'overlay.css'), 'utf8');
  for (const it of items) {
    const full = it.fullPage === true;
    await page.setContent(`<!doctype html><html><head><meta charset="utf-8"><style>${css}</style></head>
      <body class="${full ? 'full' : ''}"><div id="root">${it.html}</div></body></html>`);
    await page.evaluate(() => document.fonts.ready);
    const out = path.join(outDir, it.name + '.png');
    if (full) await page.screenshot({ path: out, omitBackground: !it.opaque });
    else await page.locator('#root > *').first().screenshot({ path: out, omitBackground: true });
  }
  await browser.close();
})();
