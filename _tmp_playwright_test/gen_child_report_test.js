// 本機生成一次完整兒童報告測試（會呼叫 Gemini API，產生費用）
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const BASE_URL = 'https://brainwave-child-4y55eiw93-nayahdatas-projects.vercel.app/';
const DOWNLOAD_DIR = path.resolve(__dirname, 'downloads');

(async () => {
  if (!fs.existsSync(DOWNLOAD_DIR)) fs.mkdirSync(DOWNLOAD_DIR, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1600, height: 1200 },
    acceptDownloads: true,
  });
  const page = await context.newPage();

  page.on('console', msg => {
    const t = msg.text();
    if (t.includes('[summaryPage]') || t.includes('error') || t.includes('Error')) {
      console.log('[console]', t.slice(0, 300));
    }
  });
  page.on('pageerror', err => console.log('[pageerror]', err.message));

  console.log('前往', BASE_URL);
  await page.goto(BASE_URL, { waitUntil: 'load', timeout: 60000 });
  await page.waitForSelector('text=單筆生成', { timeout: 30000 });
  await page.waitForTimeout(500);

  console.log('點擊「單筆生成」');
  await page.click('text=單筆生成');
  await page.waitForTimeout(800);

  console.log('填寫姓名/年齡/日期');
  await page.fill('input[placeholder="輸入姓名..."]', '測試小明');
  await page.fill('input[placeholder="例：8歲"]', '8歲');
  await page.fill('input[placeholder="例：2026/02/28"]', '2026/08/14');

  // 設定有落差的腦波數值，確保各章節有分化（非全部50）
  const sliderValues = {
    theta: 72, highAlpha: 65, lowAlpha: 40, lowBeta: 58,
    highBeta: 78, highGamma: 55, lowGamma: 35, focus: 60, relaxation: 38,
  };
  const rows = await page.$$('input[type="range"]');
  const keys = Object.keys(sliderValues);
  for (let i = 0; i < rows.length && i < keys.length; i++) {
    const val = sliderValues[keys[i]];
    await rows[i].evaluate((el, v) => {
      const proto = Object.getPrototypeOf(el);
      const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
      setter.call(el, v);
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    }, val);
  }
  await page.waitForTimeout(500);

  console.log('點擊「開始生成兒童專屬報告」進入工作站');
  await page.click('text=開始生成兒童專屬報告');
  await page.waitForTimeout(1500);

  console.log('點擊「啟動完整報告生成」，開始呼叫 Gemini API（需要數分鐘）...');
  await page.click('text=/啟動完整報告生成/');

  // CONCURRENCY=1（App.tsx 既有設定，不更動），實測 33% 耗時 20 分鐘 → 全部跑完約 60-65 分鐘。
  // 設 100 分鐘上限，確保絕不會在生成過程中把瀏覽器關閉（關閉=記憶體內容全部遺失，無法恢復）。
  const WAIT_MINUTES = 100;
  console.log(`等待下載事件（PDF 完成後自動下載）... 最長等待 ${WAIT_MINUTES} 分鐘`);
  const downloadPromise = page.waitForEvent('download', { timeout: WAIT_MINUTES * 60 * 1000 });

  // 同時輪詢狀態文字，方便觀察進度
  const pollInterval = setInterval(async () => {
    try {
      const text = await page.evaluate(() => document.body.innerText.slice(0, 200));
      console.log('[狀態]', new Date().toISOString(), text.split('\n')[0]);
    } catch {}
  }, 20000);

  try {
    const download = await downloadPromise;
    clearInterval(pollInterval);
    const savePath = path.join(DOWNLOAD_DIR, 'test_child_report.pdf');
    await download.saveAs(savePath);
    console.log('✅ PDF 已儲存至', savePath);
  } catch (e) {
    clearInterval(pollInterval);
    console.error('❌ 未偵測到下載事件:', e.message);
    const finalText = await page.evaluate(() => document.body.innerText.slice(0, 500)).catch(() => '');
    console.log('最後頁面文字:', finalText);
    await page.screenshot({ path: path.join(DOWNLOAD_DIR, 'failure_screenshot.png'), fullPage: true }).catch(() => {});
  }

  await browser.close();
})();
