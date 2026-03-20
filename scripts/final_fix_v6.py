import re

with open("web/terminal.html", "r") as f:
    content = f.read()

# 1. REMOVE DEBUG LOGS AND FIX THE OVERWRITE BUG
# The bug was: updateTrendChart was calling updateExchangeTable(rawData.tokens[token])
# which overwrote the aggregated full history with just the latest hour's data (often 0).

content = re.sub(r"console\.log\(.*?\);", "", content)

# Remove the redundant/broken refresh at the end of updateTrendChart
content = re.sub(
    r"setTimeout\(\(\) => \{ isUpdatingToken = false; \}, 100\);\n  // Force a full-data refresh of sub-charts to ensure single-click works\n  updateExchangeTable\(rawData\.tokens\[token\]\);\n  updateSankey\(rawData\.tokens\[token\]\);",
    "setTimeout(() => { isUpdatingToken = false; }, 100);",
    content
)

# 2. IMPROVE updateDashboard to ensure it always has data
# Use aggregateRangeData(null, null) as the primary source for the initial view
content = re.sub(
    r"const fullHistory = aggregateRangeData\(null, null\);",
    "const fullHistory = aggregateRangeData(null, null);",
    content
)

# 3. Ensure Sankey node padding is robust
content = re.sub(
    r"pad: Math\.max\(15, 150 / \(nodeIdx \|\| 1\)\),",
    "pad: Math.max(20, Math.min(100, 500 / (nodeIdx || 1))),",
    content
)

with open("web/terminal.html", "w") as f:
    f.write(content)
