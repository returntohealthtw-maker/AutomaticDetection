const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1200 } });
  page.on('pageerror', err => console.log('[pageerror]', err.message));
  await page.goto('http://localhost:5173/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(500);
  await page.click('text=單筆生成');
  await page.waitForTimeout(800);
  await page.screenshot({ path: 'shot_2_after_single.png', fullPage: true });
  console.log('DONE step2 screenshot');
  await browser.close();
})();
