#!/usr/bin/env python3
"""使用 Playwright 截图验证 GitHub Pages 前端

使用 headless 模式，完全不会抢夺焦点或打开窗口。
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# 修复 Python 3.13 的 Playwright 异步问题
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '0'
os.environ['PLAYWRIGHT_PYTHON_DISABLE_ASYNC_CHECK'] = '1'

from playwright.sync_api import sync_playwright

GITHUB_PAGES_URL = "https://melroseee-e.github.io/data-monitoring/"
SCREENSHOT_DIR = Path(__file__).parent.parent / "screenshots"

def take_screenshot():
    """截图 TGE Net Flow 页面"""

    print(f"📸 开始截图: {GITHUB_PAGES_URL}")
    print(f"💾 保存目录: {SCREENSHOT_DIR}")

    with sync_playwright() as p:
        # 使用 headless 模式（不会抢焦点）
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()

        try:
            # 访问页面
            print("🌐 加载页面...")
            page.goto(GITHUB_PAGES_URL, wait_until='networkidle', timeout=30000)

            # 等待页面加载完成
            page.wait_for_selector('#tge-tab', timeout=10000)
            print("✅ 页面加载完成")

            # 点击 TGE Net Flow tab
            print("🖱️  切换到 TGE Net Flow tab...")
            page.click('#tge-tab')

            # 等待图表渲染
            page.wait_for_timeout(2000)

            # 检查是否有图表
            chart_exists = page.query_selector('#tge-cumulative-chart')
            if not chart_exists:
                print("❌ 未找到 TGE 图表元素")
                return False

            print("✅ TGE 图表已渲染")

            # 截图
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = SCREENSHOT_DIR / f"tge_netflow_{timestamp}.png"

            page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"✅ 截图已保存: {screenshot_path}")

            # 验证代币列表
            print("\n📊 验证代币列表...")
            tokens_found = []

            # 检查 summary table
            table = page.query_selector('#tge-summary-table')
            if table:
                rows = table.query_selector_all('tbody tr')
                for row in rows:
                    token_cell = row.query_selector('td:first-child')
                    if token_cell:
                        token_name = token_cell.inner_text().strip()
                        tokens_found.append(token_name)

                print(f"✅ 找到 {len(tokens_found)} 个代币:")
                for token in tokens_found:
                    print(f"   - {token}")

            # 检查是否有 pending 提示
            pending_rows = page.query_selector_all('tbody tr.pending-row')
            if pending_rows:
                print(f"\n⏳ {len(pending_rows)} 个代币正在回填中")

            return True

        except Exception as e:
            print(f"❌ 错误: {e}")
            return False

        finally:
            browser.close()

if __name__ == "__main__":
    success = take_screenshot()
    sys.exit(0 if success else 1)
