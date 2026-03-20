import os
import sys
from pathlib import Path
import time
import subprocess

os.environ['PLAYWRIGHT_PYTHON_DISABLE_ASYNC_CHECK'] = '1'
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = Path(__file__).parent.parent / "screenshots" / "terminal_tokens"

def capture_all_tokens():
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()

        print("🌐 Loading http://localhost:8899/web/terminal.html ...")
        page.goto("http://localhost:8899/web/terminal.html", wait_until='networkidle')
        page.wait_for_timeout(3000)

        # Get all token names from the list
        token_elements = page.query_selector_all('.token-item')
        print(f"Found {len(token_elements)} tokens.")

        for i in range(len(token_elements)):
            # Re-fetch elements to avoid stale references
            tokens = page.query_selector_all('.token-item')
            if i >= len(tokens):
                break
                
            token = tokens[i]
            token_name = token.get_attribute('data-token')
            print(f"📸 Capturing {token_name} ...")
            
            token.click()
            page.wait_for_timeout(1500) # Wait for chart to render
            
            screenshot_path = SCREENSHOT_DIR / f"{token_name}.png"
            page.screenshot(path=str(screenshot_path))
            
        print("✅ Done!")
        browser.close()

if __name__ == "__main__":
    capture_all_tokens()
