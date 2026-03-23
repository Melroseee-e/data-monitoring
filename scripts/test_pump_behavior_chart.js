const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

async function ensureDir(dir) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

async function run() {
  const baseUrl = process.env.BASE_URL || 'http://127.0.0.1:8765';
  const url = `${baseUrl}/web/pump_behavior_chart.html`;
  const outDir = path.join(process.cwd(), 'screenshots', 'pump_behavior_chart_verify');
  await ensureDir(outDir);

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1720, height: 980 } });

  try {
    await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForSelector('#mainChart canvas', { timeout: 60000 });
    await page.waitForTimeout(1500);

    await page.screenshot({ path: path.join(outDir, '01_initial.png'), fullPage: true });

    await page.click('.chip[data-cat="official_exchange"]');
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(outDir, '02_toggle_official.png'), fullPage: true });

    await page.selectOption('#minAmount', '0.5');
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(outDir, '03_min_amount_0_5.png'), fullPage: true });

    await page.click('.chip[data-cat="whale_netflow"]');
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(outDir, '04_only_buyback_bottom.png'), fullPage: true });

    await page.click('.chip[data-cat="whale_netflow"]');
    await page.waitForTimeout(600);
    await page.fill('#searchInput', 'Hyperunit');
    await page.waitForTimeout(1200);
    await page.screenshot({ path: path.join(outDir, '05_search_hyperunit.png'), fullPage: true });

    const chartBox = await page.locator('#mainChart').boundingBox();
    if (chartBox) {
      await page.mouse.move(chartBox.x + chartBox.width * 0.66, chartBox.y + chartBox.height * 0.34);
      await page.waitForTimeout(900);
      await page.screenshot({ path: path.join(outDir, '06_hover_tooltip.png'), fullPage: true });
    }

    console.log('Screenshots generated at:', outDir);
    console.log('Checked interactions: toggle category, min amount filter, buyback-only view, search, hover tooltip.');
  } finally {
    await browser.close();
  }
}

run().catch((err) => {
  console.error('test_pump_behavior_chart failed:', err);
  process.exit(1);
});
