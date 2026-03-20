import os
import sys
from pathlib import Path
import time

os.environ['PLAYWRIGHT_PYTHON_DISABLE_ASYNC_CHECK'] = '1'
from playwright.sync_api import sync_playwright

def debug():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        page.goto("http://localhost:8899/web/terminal.html", wait_until='networkidle')
        page.wait_for_timeout(2000)
        
        print("Switching to BIRB...")
        page.click(".token-item[data-token='BIRB']")
        page.wait_for_timeout(2000)
        
        # Check Sankey internal state
        sankey_debug = page.evaluate("""
            () => {
                const token = 'BIRB';
                const data = rawData.tokens[token];
                
                // Simulate what updateSankey sees
                const nodeLabels = [token];
                const linkValues = [];
                
                if (data.deployments) {
                    data.deployments.forEach(dep => {
                        Object.entries(dep.exchange_flows).forEach(([ex, flows]) => {
                            if(flows.inflow > 0) linkValues.push(flows.inflow);
                            if(flows.outflow > 0) linkValues.push(flows.outflow);
                        });
                    });
                }
                
                return {
                    token: token,
                    hasDeployments: !!data.deployments,
                    deploymentCount: data.deployments ? data.deployments.length : 0,
                    firstDepExchanges: data.deployments && data.deployments[0] ? Object.keys(data.deployments[0].exchange_flows) : [],
                    linkValuesFound: linkValues.length
                };
            }
        """)
        print("Sankey Debug Logic Result:", sankey_debug)
        
        browser.close()

if __name__ == "__main__":
    debug()
