import os
import sys
from pathlib import Path
import time

os.environ['PLAYWRIGHT_PYTHON_DISABLE_ASYNC_CHECK'] = '1'
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = Path(__file__).parent.parent / "screenshots" / "interactive_tests"

def run_interactive_tests():
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()

        errors = []
        page.on("console", lambda msg: print(f"Browser Console [{msg.type}]: {msg.text}"))
        page.on("pageerror", lambda err: errors.append(str(err)))

        print("🌐 Step 1: Loading page...")
        page.goto("http://localhost:8899/web/terminal.html", wait_until='networkidle')
        page.wait_for_timeout(2000)
        
        page.screenshot(path=str(SCREENSHOT_DIR / "01_initial_load.png"))
        print("✅ Initial load successful.")

        print("\n🌗 Step 2: Testing Light Mode (Cosmic Latte)...")
        theme_btn = page.locator("#themeToggle")
        theme_btn.click()
        page.wait_for_timeout(1000)
        
        is_light = page.evaluate("document.body.classList.contains('theme-light')")
        print(f"Theme changed to light: {is_light}")
        page.screenshot(path=str(SCREENSHOT_DIR / "02_light_mode.png"))

        print("\n🖱️ Step 3: Testing Token Switch (Selecting SKR)...")
        skr_btn = page.locator(".token-item[data-token='SKR']")
        skr_btn.click()
        page.wait_for_timeout(2000) # wait for plotly to render
        
        header_title = page.locator("#headerTitle").inner_text()
        print(f"Header updated to: {header_title.strip()}")
        page.screenshot(path=str(SCREENSHOT_DIR / "03_skr_selected.png"))

        print("\n🔍 Step 4: Testing Chart Interaction (Clicking 1W zoom on Plotly)...")
        # Plotly range selector buttons have class 'updatemenu-button'
        zoom_1w = page.locator("text='1W'")
        if zoom_1w.count() > 0:
            zoom_1w.first.click()
            page.wait_for_timeout(1500)
            page.screenshot(path=str(SCREENSHOT_DIR / "04_skr_1w_zoomed.png"))
            print("✅ Clicked 1W zoom button.")
        else:
            print("⚠️ Could not find '1W' zoom button.")

        print("\n📊 Step 5: Testing Sankey Interaction (Hovering over node)...")
        sankey_nodes = page.locator("g.sankey-node")
        if sankey_nodes.count() > 0:
            sankey_nodes.first.hover()
            page.wait_for_timeout(1000)
            page.screenshot(path=str(SCREENSHOT_DIR / "05_sankey_hover.png"))
            print("✅ Hovered over Sankey node.")

        print("\n✅ All interactive tests completed.")
        if errors:
            print(f"❌ Encountered {len(errors)} page errors during tests:")
            for e in errors:
                print(e)
        else:
            print("🎉 No JavaScript errors detected during interactions!")

        browser.close()

if __name__ == "__main__":
    run_interactive_tests()
