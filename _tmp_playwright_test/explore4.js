const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1200 } });
  await page.goto('http://localhost:5173/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(500);
  await page.click('text=單筆生成');
  await page.waitForTimeout(500);
  await page.locator('input[placeholder="輸入姓名..."]').fill('測試小朋友');
  await page.locator('input[placeholder="例：8歲"]').fill('8');
  await page.click('text=開始生成兒童專屬報告');
  await page.waitForTimeout(1500);
  await page.screenshot({ path: 'shot_3_workstation.png', fullPage: true });
  console.log('DONE workstation screenshot');
  await browser.close();
})();
