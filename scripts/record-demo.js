// Record AMA demo video via Playwright
const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    recordVideo: {
      dir: path.join(__dirname, '..', 'public'),
      size: { width: 1280, height: 720 },
    },
  });

  const page = await context.newPage();
  const demoPath = 'file:///' + path.join(__dirname, '..', 'public', 'demo.html').replace(/\\/g, '/');
  console.log('Opening:', demoPath);
  await page.goto(demoPath, { waitUntil: 'domcontentloaded' });

  // Wait for full animation sequence: ~15 seconds
  await page.waitForTimeout(18000);

  // Close and save video
  await context.close();
  await browser.close();

  // Rename the .webm file
  const fs = require('fs');
  const dir = path.join(__dirname, '..', 'public');
  const files = fs.readdirSync(dir).filter(f => f.endsWith('.webm'));
  if (files.length > 0) {
    const src = path.join(dir, files[0]);
    const dst = path.join(dir, 'ama-demo.webm');
    if (fs.existsSync(dst)) fs.unlinkSync(dst);
    fs.renameSync(src, dst);
    console.log('Video saved:', dst);
  }
  console.log('Done.');
})().catch(e => { console.error(e.message); process.exit(1); });
