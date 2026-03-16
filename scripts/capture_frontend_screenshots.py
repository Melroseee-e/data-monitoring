#!/usr/bin/env python3
"""
Capture screenshots of the frontend to verify TGE data display.
"""
from playwright.sync_api import sync_playwright
import time

URL = "https://melroseee-e.github.io/data-monitoring/"
SCREENSHOTS_DIR = "/Users/melrose/Headquarter/Crypto Intel/On-Chain Data/data-monitoring(chen)/screenshots"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})

        print(f"Navigating to {URL}...")
        page.goto(URL)
        page.wait_for_load_state('networkidle')
        time.sleep(3)  # Extra wait for charts to render

        # Screenshot 1: Overview tab
        print("Capturing overview tab...")
        page.screenshot(path=f"{SCREENSHOTS_DIR}/01-overview-tab.png", full_page=True)

        # Screenshot 2: Click TGE Net Flow tab
        print("Clicking TGE Net Flow tab...")
        page.click('button[data-tab="tge-chart"]')
        time.sleep(2)  # Wait for chart to render
        page.screenshot(path=f"{SCREENSHOTS_DIR}/02-tge-netflow-tab.png", full_page=True)

        # Screenshot 3: TGE chart with all tokens visible
        print("Capturing TGE chart detail...")
        tge_chart = page.locator('#tge-cumulative-chart')
        if tge_chart.is_visible():
            tge_chart.screenshot(path=f"{SCREENSHOTS_DIR}/03-tge-chart-detail.png")

        # Screenshot 4: TGE summary table
        print("Capturing TGE summary table...")
        tge_table = page.locator('#tge-summary-table')
        if tge_table.is_visible():
            tge_table.screenshot(path=f"{SCREENSHOTS_DIR}/04-tge-summary-table.png")

        # Screenshot 5: Daily Heatmap tab
        print("Clicking Daily Heatmap tab...")
        page.click('button[data-tab="daily-heatmap"]')
        time.sleep(2)
        page.screenshot(path=f"{SCREENSHOTS_DIR}/05-daily-heatmap-tab.png", full_page=True)

        # Screenshot 6: Daily Chart tab
        print("Clicking Daily Chart tab...")
        page.click('button[data-tab="daily-chart"]')
        time.sleep(2)
        page.screenshot(path=f"{SCREENSHOTS_DIR}/06-daily-chart-tab.png", full_page=True)

        browser.close()
        print(f"\nAll screenshots saved to {SCREENSHOTS_DIR}/")
        print("✓ Overview tab")
        print("✓ TGE Net Flow tab (full page)")
        print("✓ TGE chart detail")
        print("✓ TGE summary table")
        print("✓ Daily Heatmap tab")
        print("✓ Daily Chart tab")

if __name__ == "__main__":
    main()
