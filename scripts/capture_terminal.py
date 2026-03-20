import os
import sys
from pathlib import Path

os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '0'
os.environ['PLAYWRIGHT_PYTHON_DISABLE_ASYNC_CHECK'] = '1'

from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = Path(__file__).parent.parent / "screenshots"

def check_terminal_ui():
    SCREENSHOT_DIR.mkdir(exist_ok=True)
    screenshot_path = SCREENSHOT_DIR / "terminal_debug.png"
    
    html_path = Path(__file__).parent.parent / "web" / "terminal.html"
    file_url = f"file://{html_path.resolve()}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()

        page.on("console", lambda msg: print(f"Console [{msg.type}]: {msg.text}"))
        page.on("pageerror", lambda err: print(f"Page Error: {err}"))

        print(f"🌐 Loading {file_url} ...")
        page.goto(file_url, wait_until='networkidle')

        print("⏳ Waiting for charts to render...")
        page.wait_for_timeout(3000)

        page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"✅ Screenshot saved: {screenshot_path}")

        browser.close()

if __name__ == "__main__":
    check_terminal_ui()
