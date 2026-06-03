// Post demo video to Twitter
const { chromium } = require('playwright');
const path = require('path');

const TWEET = 'Scanned my dev PC. Found 457 AI agents.\nMost unmanaged. API keys everywhere. Zero tracking.\n\nBuilt AMA. Open source. MIT.\n\ngithub.com/xzwyjia-pixel/ama';
const VIDEO = path.join(__dirname, '..', 'public', 'ama-demo.mp4');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  await page.goto('https://x.com/home', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3000);

  const url = page.url();
  if (url.includes('login') || url.includes('onboarding')) {
    console.log('Please log in to Twitter in the browser window.');
    await page.waitForFunction(() => !window.location.href.includes('login') && !window.location.href.includes('onboarding'), { timeout: 120000 }).catch(() => {});
    await page.waitForTimeout(2000);
    await page.goto('https://x.com/home', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);
  }

  console.log('Clicking compose area...');
  // Click the "What's happening" / "Post" area to open composer
  await page.click('a[href="/compose/post"]').catch(() => {});
  await page.click('[aria-label="Post"]').catch(() => {});
  await page.click('text=What is happening').catch(() => {});
  await page.waitForTimeout(2000);

  // Try multiple selectors for the textbox
  let found = false;
  for (const sel of ['div[role="textbox"]', '[contenteditable="true"]', '.public-DraftEditor-content', '[data-text="true"]']) {
    try {
      const el = page.locator(sel).first();
      if (await el.isVisible({ timeout: 2000 }).catch(() => false)) {
        await el.click();
        await page.keyboard.type(TWEET, { delay: 5 });
        found = true;
        console.log('Typed using:', sel);
        break;
      }
    } catch {}
  }

  if (!found) {
    console.log('Could not find textbox. Pasting via clipboard...');
    await page.evaluate((text) => {
      navigator.clipboard.writeText(text);
    }, TWEET);
    await page.keyboard.press('Control+v');
    console.log('Pasted.');
  }

  await page.waitForTimeout(500);
  console.log('Text done');

  console.log('Uploading video...');
  const input = page.locator('input[type="file"]').first();
  await input.setInputFiles(VIDEO);
  console.log('Video attached, waiting for processing...');
  await page.waitForTimeout(10000);

  console.log('Clicking Post...');
  const postBtn = page.locator('[data-testid="tweetButton"], [data-testid="tweetButtonInline"], button:has-text("Post")').first();
  await postBtn.click({ timeout: 10000 }).catch(() => {});
  await page.waitForTimeout(5000);

  console.log('Posted! Verify at https://x.com/xzwyjia');
  await page.waitForTimeout(2000);
  await browser.close();
})().catch(e => { console.error(e.message); process.exit(1); });
