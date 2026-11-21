// Renders promo.html frame-by-frame into an MP4 (or a few still frames).
// usage: node render_video.js A out.mp4            -> full video
//        node render_video.js A outdir --stills 1,4.5,9
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path'), fs = require('fs');
const [, , ver = 'A', out, flag, list] = process.argv;
const FPS = 30;
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => console.error('PAGE ERROR', e.message));
  await page.goto('file://' + path.join(__dirname, 'promo.html') + '?v=' + ver);
  await page.waitForFunction(() => window.READY === true);
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(() => Promise.all([...document.images].map(i => i.decode())));
  const shot = async t => { await page.evaluate(t => window.seek(t), t);
    await page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));
    return page.screenshot({ type: 'png' }); };
  if (flag === '--stills') {
    fs.mkdirSync(out, { recursive: true });
    for (const t of list.split(',').map(Number)) fs.writeFileSync(path.join(out, `${ver}-${t.toFixed(2).padStart(5, '0')}s.png`), await shot(t));
  } else {
    const dur = await page.evaluate(() => window.DURATION);
    const n = Math.round(dur * FPS);
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-',
      '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=48000', '-shortest',
      '-c:v', 'libx264', '-profile:v', 'high', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', '-r', String(FPS),
      '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', out], { stdio: ['pipe', 'inherit', 'inherit'] });
    const t0 = Date.now();
    for (let i = 0; i < n; i++) {
      const buf = await shot(i / FPS);
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      if (i % 90 === 0) console.log(`frame ${i}/${n}  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
    }
    ff.stdin.end(); await new Promise(r => ff.on('close', r));
    console.log('saved', out);
  }
  await browser.close();
})();
