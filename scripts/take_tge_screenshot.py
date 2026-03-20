#!/usr/bin/env python3
"""Take screenshot of TGE Net Flow tab on GitHub Pages"""

from playwright.sync_api import sync_playwright
from pathlib import Path

# Target URL and output path
url = "https://melroseee-e.github.io/data-monitoring/"
output_path = Path(__file__).parent.parent / "screenshots" / "tge_netflow.png"
output_path.parent.mkdir(exist_ok=True)

print(f"📸 Taking screenshot of: {url}")
print(f"💾 Output: {output_path}")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})

    # Navigate to page
    print("🌐 Loading page...")
    page.goto(url, wait_until='networkidle')

    # Click TGE tab (using text selector)
    print("🖱️  Clicking TGE Net Flow tab...")
    page.click('button.tab-btn:has-text("TGE Net Flow")')

    # Wait for content to render
    page.wait_for_timeout(2000)

    # Take screenshot
    print("📷 Capturing screenshot...")
    page.screenshot(path=str(output_path), full_page=True)

    browser.close()

print(f"✅ Screenshot saved: {output_path}")
