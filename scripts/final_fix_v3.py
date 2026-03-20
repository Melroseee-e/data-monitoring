import re

with open("web/terminal.html", "r") as f:
    content = f.read()

# 1. THE ROOT CAUSE: Time Range Mismatch on Initial Click
# When we click a token, Plotly might trigger a relayout event with the OLD token's range
# or an undefined range. We need to ensure updateTrendChart initializes with the CORRECT data.

# 2. Add an explicit 'initial' flag to prevent relayout loops
content = re.sub(
    r"let currentTrendView = 'daily';",
    "let currentTrendView = 'daily';\nlet isUpdatingToken = false;",
    content
)

# 3. Guard plotly_relayout with the flag
content = re.sub(
    r"chartDiv\.on\('plotly_relayout', function\(eventData\) \{",
    "chartDiv.on('plotly_relayout', function(eventData) {\n    if (isUpdatingToken) return;",
    content
)

# 4. Wrap updateDashboard with the flag and FORCE re-render logic
content = re.sub(
    r"function updateDashboard\(\) \{",
    "function updateDashboard() {\n  isUpdatingToken = true;",
    content
)

# Add reset of flag at the end of updateTrendChart (which is the last thing called)
content = re.sub(
    r"Plotly\.newPlot\(chartDiv, plotTraces, layout, \{displayModeBar: false, responsive: true\}\);",
    "Plotly.newPlot(chartDiv, plotTraces, layout, {displayModeBar: false, responsive: true});\n  setTimeout(() => { isUpdatingToken = false; }, 100);",
    content
)

# 5. Fix the "BIRB No data" issue: 
# The searchSources logic in relayout was finding NO data because 'start' and 'end' 
# were from the PREVIOUS token's scale (e.g. AZTEC's Jan range doesn't fit BIRB's Mar range).
# We MUST reset range display on token switch.

# 6. Final UX Polish: Remove 'No data' text quickly
content = re.sub(
    r"document\.getElementById\('sankeyChart'\)\.innerHTML = '<div style=\"padding:20px;text-align:center;\">Loading Routing Data\.\.\.</div>';",
    "// document.getElementById('sankeyChart').innerHTML = '';",
    content
)

with open("web/terminal.html", "w") as f:
    f.write(content)
