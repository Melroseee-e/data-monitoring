import os
import sys
from pathlib import Path
import time

os.environ['PLAYWRIGHT_PYTHON_DISABLE_ASYNC_CHECK'] = '1'
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = Path(__file__).parent.parent / "screenshots" / "debug_click"

def debug_click():
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()

        page.on("console", lambda msg: print(f"Console: {msg.text}"))
        page.on("pageerror", lambda err: print(f"Error: {err}"))

        print("🌐 Loading terminal.html...")
        page.goto("http://localhost:8899/web/terminal.html", wait_until='networkidle')
        page.wait_for_timeout(3000)
        
        # Identify second token (first is already selected by default)
        token_items = page.query_selector_all('.token-item')
        if len(token_items) < 2:
            print("Not enough tokens to test.")
            return
            
        target = token_items[1]
        token_name = target.get_attribute('data-token')
        print(f"🖱️ Performing SINGLE CLICK on {token_name}...")
        
        target.click()
        
        print("⏳ Waiting for data to appear (3 seconds)...")
        page.wait_for_timeout(3000)
        
        # Verify if chart has content
        has_chart_data = page.evaluate("() => { const gd = document.getElementById('trendChart'); return !!(gd && gd.data && gd.data.length > 0); }")
        has_sankey_data = page.evaluate("() => { const gd = document.getElementById('sankeyChart'); return !!(gd && gd.data && gd.data.length > 0); }")
        
        print(f"📈 Trend Chart has data: {has_chart_data}")
        print(f"🌊 Sankey Chart has data: {has_sankey_data}")
        
        page.screenshot(path=str(SCREENSHOT_DIR / "single_click_result.png"))
        
        if not has_chart_data or not has_sankey_data:
            print("⚠️ FAILED: Data missing after single click. Testing SECOND click...")
            target.click()
            page.wait_for_timeout(2000)
            has_chart_data_2 = page.evaluate("() => { const gd = document.getElementById('trendChart'); return !!(gd && gd.data && gd.data.length > 0); }")
            print(f"📈 Trend Chart has data after 2nd click: {has_chart_data_2}")
            page.screenshot(path=str(SCREENSHOT_DIR / "double_click_result.png"))
        else:
            print("✅ SUCCESS: Data loaded on single click.")

        browser.close()

if __name__ == "__main__":
    debug_click()
