import os
import sys
from pathlib import Path
import time

os.environ['PLAYWRIGHT_PYTHON_DISABLE_ASYNC_CHECK'] = '1'
from playwright.sync_api import sync_playwright

def debug():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.on("console", lambda msg: print(f"Console: {msg.text}"))
        page.on("pageerror", lambda err: print(f"Error: {err}"))
        
        print("🌐 Loading terminal/index.html...")
        page.goto("http://localhost:8899/terminal/index.html", wait_until='networkidle')
        page.wait_for_timeout(3000)
        
        # Check components
        stats = page.evaluate("""
            () => {
                const trend = document.getElementById('trendChart');
                const sankey = document.getElementById('sankeyChart');
                return {
                    trendHasData: !!(trend && trend.data && trend.data.length > 0),
                    sankeyHasData: !!(sankey && sankey.data && sankey.data.length > 0),
                    sankeyText: sankey.innerText,
                    tokenCount: document.querySelectorAll('.token-item').length
                };
            }
        """)
        print("Stats:", stats)
        
        page.screenshot(path="screenshots/terminal_final_debug.png")
        
        # Switch to PUMP
        print("Clicking PUMP...")
        page.click("text='PUMP'")
        page.wait_for_timeout(2000)
        page.screenshot(path="screenshots/terminal_final_pump.png")
        
        browser.close()

if __name__ == "__main__":
    debug()
