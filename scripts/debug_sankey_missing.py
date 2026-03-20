import os
import sys
from pathlib import Path
import time

os.environ['PLAYWRIGHT_PYTHON_DISABLE_ASYNC_CHECK'] = '1'
from playwright.sync_api import sync_playwright

def debug_sankey():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.on("console", lambda msg: print(f"Console: {msg.text}"))
        
        page.goto("http://localhost:8899/web/terminal.html", wait_until='networkidle')
        page.wait_for_timeout(2000)
        
        print("Clicking BIRB...")
        page.click(".token-item[data-token='BIRB']")
        page.wait_for_timeout(2000)
        
        # Log properties of the sankey element
        log_js = """
        () => {
            const gd = document.getElementById('sankeyChart');
            return {
                innerHTML: gd.innerHTML.substring(0, 100),
                dataLength: gd.data ? gd.data.length : 'N/A',
                display: gd.style.display,
                visibility: gd.style.visibility,
                width: gd.clientWidth,
                height: gd.clientHeight
            };
        }
        """
        result = page.evaluate(log_js)
        print("Sankey state:", result)
        
        browser.close()

if __name__ == "__main__":
    debug_sankey()
