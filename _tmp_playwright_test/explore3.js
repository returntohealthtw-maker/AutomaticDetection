const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1200 } });
  await page.goto('http://localhost:5173/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(500);
  await page.click('text=單筆生成');
  await page.waitForTimeout(800);
  const inputs = await page.$$eval('input', els => els.map(e => ({
    type: e.type, name: e.name, id: e.id, placeholder: e.placeholder,
    min: e.min, max: e.max, value: e.value, className: e.className.slice(0,50)
  })));
  console.log(JSON.stringify(inputs, null, 2));
  await browser.close();
})();
