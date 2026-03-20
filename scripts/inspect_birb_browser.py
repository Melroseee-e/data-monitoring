import os
import sys
from pathlib import Path
import time

os.environ['PLAYWRIGHT_PYTHON_DISABLE_ASYNC_CHECK'] = '1'
from playwright.sync_api import sync_playwright

def inspect():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("🌐 Loading terminal.html...")
        page.goto("http://localhost:8899/web/terminal.html", wait_until='networkidle')
        page.wait_for_timeout(3000)
        
        print("Clicking BIRB...")
        page.click(".token-item[data-token='BIRB']")
        page.wait_for_timeout(2000)
        
        # Inspect data in JS
        data_state = page.evaluate("""
            () => {
                const birbRaw = rawData.tokens['BIRB'];
                const birbDaily = dailyData.filter(d => d.tokens && d.tokens['BIRB']);
                const birbHistory = historyData ? historyData.filter(d => d.tokens && d.tokens['BIRB']) : [];
                
                return {
                    rawTotalInflow: birbRaw ? birbRaw.total_inflow : 'N/A',
                    dailyRecordCount: birbDaily.length,
                    historyRecordCount: birbHistory.length,
                    firstDailyDate: birbDaily.length > 0 ? birbDaily[0].date : 'N/A',
                    lastDailyDate: birbDaily.length > 0 ? birbDaily[birbDaily.length-1].date : 'N/A'
                };
            }
        """)
        print("Browser Data State for BIRB:", data_state)
        
        # Check if chart exists
        chart_info = page.evaluate("""
            () => {
                const gd = document.getElementById('trendChart');
                return {
                    hasData: !!(gd && gd.data && gd.data.length > 0),
                    traceCount: gd && gd.data ? gd.data.length : 0,
                    firstX: gd && gd.data && gd.data[0] && gd.data[0].x ? gd.data[0].x[0] : 'N/A'
                };
            }
        """)
        print("Chart State for BIRB:", chart_info)
        
        page.screenshot(path="screenshots/birb_inspection.png")
        browser.close()

if __name__ == "__main__":
    inspect()
