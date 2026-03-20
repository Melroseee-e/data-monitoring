#!/usr/bin/env python3
"""Find TGE tab button"""

from playwright.sync_api import sync_playwright

url = "https://melroseee-e.github.io/data-monitoring/"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})

    page.goto(url, wait_until='networkidle')

    # Find all buttons
    buttons = page.locator('button.tab-btn').all()
    print(f"Found {len(buttons)} tab buttons:")
    for i, btn in enumerate(buttons):
        text = btn.inner_text().strip()
        print(f"  [{i}] '{text}'")

    browser.close()
