// Saves thumbnail-A/B/C.png (1080x1920) from thumb.html into ../final-videos
const { chromium } = require('playwright'); const path = require('path');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  for (const v of ['A', 'B', 'C']) {
    await p.goto('file://' + path.join(__dirname, 'thumb.html') + '?v=' + v);
    await p.waitForFunction(() => window.READY); await p.evaluate(() => document.fonts.ready);
    await p.evaluate(() => Promise.all([...document.images].map(i => i.decode())));
    await p.screenshot({ path: path.join(__dirname, '..', 'final-videos', `thumbnail-${v}.png`) });
  }
  await b.close();
})();
