import re

with open("web/terminal.html", "r") as f:
    content = f.read()

# 1. Optimize token selection: Update active class instead of re-rendering the whole list
new_click_handler = """  document.querySelectorAll('.token-item').forEach(el => {
    el.addEventListener('click', () => {
      const targetToken = el.dataset.token;
      if (selectedToken === targetToken) return;
      
      selectedToken = targetToken;
      
      // Update UI state without full re-render
      document.querySelectorAll('.token-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.token === selectedToken) {
          item.classList.add('active');
        }
      });
      
      updateDashboard();
    });
  });"""

content = re.sub(
    r"document\.querySelectorAll\('\.token-item'\)\.forEach\(el => \{.*?\}\);\n\n  updateDashboard\(\);",
    new_click_handler + "\n\n  updateDashboard();",
    content,
    flags=re.DOTALL
)

# 2. Disable Plotly entry animations for Sankey and Trend charts
# For Sankey
content = re.sub(
    r"height: Math\.max\(300, Math\.min\(600, nodeIdx \* 40\)\) // Dynamic height",
    r"height: Math.max(300, Math.min(600, nodeIdx * 40)), // Dynamic height\n    transition: { duration: 0 }",
    content
)

# For Trend
content = re.sub(
    r"yaxis: \{ gridcolor: gridColor, zerolinecolor: gridColor, tickformat: '\.2s', autorange: true, fixedrange: false \}",
    r"yaxis: { gridcolor: gridColor, zerolinecolor: gridColor, tickformat: '.2s', autorange: true, fixedrange: false },\n    transition: { duration: 0 }",
    content
)

# 3. Increase robust rendering in updateDashboard
content = re.sub(
    r"document\.getElementById\('sankeyChart'\)\.innerHTML = '<div style=\"padding:20px;text-align:center;\">Loading Routing Data\.\.\.</div>';",
    r"// Skip clearing innerHTML if we want instant update\n  // document.getElementById('sankeyChart').innerHTML = '';",
    content
)

with open("web/terminal.html", "w") as f:
    f.write(content)
