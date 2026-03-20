#!/usr/bin/env python3
"""Inspect GitHub Pages to find TGE tab selector"""

from playwright.sync_api import sync_playwright

url = "https://melroseee-e.github.io/data-monitoring/"

print(f"🔍 Inspecting: {url}")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})

    # Navigate to page
    print("🌐 Loading page...")
    page.goto(url, wait_until='networkidle')

    # Find all tab-like elements
    print("\n📋 Looking for tab elements...")

    # Try different selectors
    selectors = [
        'button',
        '[role="tab"]',
        '.tab',
        '#tge-tab',
        'a[href*="tge"]',
        '*[id*="tge"]',
        '*[class*="tge"]'
    ]

    for selector in selectors:
        elements = page.locator(selector).all()
        if elements:
            print(f"\n✅ Found {len(elements)} elements matching '{selector}':")
            for i, elem in enumerate(elements[:5]):  # Show first 5
                try:
                    text = elem.inner_text()[:50]
                    attrs = elem.evaluate('el => ({id: el.id, class: el.className})')
                    print(f"  [{i}] text='{text}' id='{attrs.get('id')}' class='{attrs.get('class')}'")
                except:
                    pass

    # Get page title
    title = page.title()
    print(f"\n📄 Page title: {title}")

    # Take a screenshot for inspection
    screenshot_path = "/tmp/github_pages_inspect.png"
    page.screenshot(path=screenshot_path, full_page=False)
    print(f"\n📸 Screenshot saved: {screenshot_path}")

    browser.close()
