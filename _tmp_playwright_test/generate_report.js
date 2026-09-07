const { chromium } = require('playwright');
const fs = require('fs');

const VALUES = {
  theta:     72,  // θ 想像力
  highAlpha: 44,  // α↑ 活力
  lowAlpha:  63,  // α↓ 平靜
  lowBeta:   58,  // β↓ 思考力
  highBeta:  82,  // β↑ 專注力
  highGamma: 35,  // γ↑ 感知力
  lowGamma:  67,  // γ↓ 愛心
  focus:     74,  // 專注
  relaxation:52,  // 放鬆
};
const NAME = '測試小朋友';
const AGE = '8';

function log(...args) {
  const line = `[${new Date().toISOString()}] ${args.join(' ')}`;
  console.log(line);
  fs.appendFileSync('progress.log', line + '\n');
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1200 }, acceptDownloads: true });
  page.on('pageerror', err => log('[pageerror]', err.message));
  page.on('console', msg => {
    const t = msg.text();
    if (/error|Error|失敗|❌/.test(t)) log('[console]', msg.type(), t.slice(0, 300));
  });

  let downloadSaved = false;
  page.on('download', async (download) => {
    const savePath = 'D:/Write program/AutomaticDetection/_tmp_playwright_test/output_report.pdf';
    await download.saveAs(savePath);
    downloadSaved = true;
    log('DOWNLOAD EVENT captured, saved to ' + savePath);
  });

  log('goto landing page');
  await page.goto('http://localhost:5173/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(500);

  log('click 單筆生成');
  await page.click('text=單筆生成');
  await page.waitForTimeout(800);

  log('fill name & age');
  await page.locator('input[placeholder="輸入姓名..."]').fill(NAME);
  await page.locator('input[placeholder="例：8歲"]').fill(AGE);

  const rangeInputs = page.locator('input[type=range]');
  const keys = ['theta', 'highAlpha', 'lowAlpha', 'lowBeta', 'highBeta', 'highGamma', 'lowGamma', 'focus', 'relaxation'];
  for (let i = 0; i < keys.length; i++) {
    const val = VALUES[keys[i]];
    const el = rangeInputs.nth(i);
    await el.evaluate((node, v) => {
      const proto = Object.getPrototypeOf(node);
      const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
      setter.call(node, String(v));
      node.dispatchEvent(new Event('input', { bubbles: true }));
      node.dispatchEvent(new Event('change', { bubbles: true }));
    }, val);
    log(`set ${keys[i]} = ${val}`);
  }
  await page.waitForTimeout(500);
  await page.screenshot({ path: 'shot_3_filled.png', fullPage: true });

  log('click enter dashboard button');
  await page.click('text=開始生成兒童專屬報告');
  await page.waitForTimeout(1500);
  await page.screenshot({ path: 'shot_3_workstation.png', fullPage: true });

  log('click full report generation button (48 sections)');
  await page.click('text=啟動完整報告生成');

  const deadline = Date.now() + 60 * 60 * 1000;
  let lastStatus = '';
  while (Date.now() < deadline) {
    await page.waitForTimeout(10000);
    let statusText = '';
    try {
      statusText = await page.evaluate(() => document.body.innerText.slice(0, 3000));
    } catch (e) { statusText = '(eval failed: ' + e.message + ')'; }
    const shortStatus = statusText.split('\n').filter(Boolean).slice(0, 10).join(' | ');
    if (shortStatus !== lastStatus) {
      log('STATUS:', shortStatus);
      lastStatus = shortStatus;
    }
    if (downloadSaved) {
      log('Download already captured, waiting a bit then exiting loop');
      await page.waitForTimeout(5000);
      break;
    }
  }
  log('loop ended, downloadSaved=' + downloadSaved);

  await page.screenshot({ path: 'shot_4_final.png', fullPage: true });

  await browser.close();
  log('browser closed, script end');
})().catch(e => { log('FATAL: ' + e.stack); process.exit(1); });
