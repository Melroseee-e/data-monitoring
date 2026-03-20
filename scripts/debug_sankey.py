import re

with open("web/terminal.html", "r") as f:
    content = f.read()

# Fix 1: The mysterious green shape is likely caused by the radial-gradient being too large or rendering artifacts.
# Let's remove the radial-gradient from body.theme-light and use a simpler background.
content = re.sub(
    r"background-image: radial-gradient\(circle at 50% 50%, rgba\(37, 99, 235, 0.02\) 0%, transparent 80%\);",
    r"background-color: #FAF8F5;",
    content
)

# Fix 2: Constrain Sankey even more and fix the "large node" problem by increasing pad.
# And ensure it's centered and has better proportions.
content = re.sub(
    r"pad: 60,",
    r"pad: 80,",
    content
)

# Fix 3: PUMP data fallback. 
# Check if selectedToken exists in rawData but maybe historyData hasn't arrived yet.
# Also fix potential indexing issues.
content = re.sub(
    r"dates.push\(entry.date \|\| entry.timestamp\);",
    r"const d = entry.date || entry.timestamp; if(!d) return; dates.push(d);",
    content
)

# Fix 4: Force a manual resize after initial render
content = re.sub(
    r"Plotly.newPlot\('sankeyChart', plotData, layout, \{displayModeBar: false, responsive: true\}\);",
    r"Plotly.newPlot('sankeyChart', plotData, layout, {displayModeBar: false, responsive: true}); setTimeout(() => Plotly.Plots.resize('sankeyChart'), 500);",
    content
)

with open("web/terminal.html", "w") as f:
    f.write(content)
