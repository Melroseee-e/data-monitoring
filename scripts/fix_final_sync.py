import re

with open("web/terminal.html", "r") as f:
    content = f.read()

# THE FIX: Plotly.newPlot generates a relayout event automatically. 
# If we change tokens, the OLD relayout handler (which filters by time) might still 
# use the OLD token's time range if it's not guarded.

# 1. Add a token-specific ID check to the relayout handler
content = re.sub(
    r"chartDiv\.on\('plotly_relayout', function\(eventData\) \{",
    "const currentInstanceToken = selectedToken;\n  chartDiv.on('plotly_relayout', function(eventData) {\n    if (isUpdatingToken || selectedToken !== currentInstanceToken) return;",
    content
)

# 2. Add an EXPLICIT refresh of Sankey and Table at the end of updateTrendChart 
# using the FULL data of the current token, ensuring it displays even if relayout doesn't fire.
refresh_logic = """  // Force a full-data refresh of sub-charts to ensure single-click works
  updateExchangeTable(rawData.tokens[token]);
  updateSankey(rawData.tokens[token]);
  
  // Reset scroll position of token list item into view if needed
  const activeItem = document.querySelector('.token-item.active');
  if (activeItem) activeItem.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
"""

content = re.sub(
    r"setTimeout\(\(\) => \{ isUpdatingToken = false; \}, 100\);",
    "setTimeout(() => { isUpdatingToken = false; }, 100);\n" + refresh_logic,
    content
)

with open("web/terminal.html", "w") as f:
    f.write(content)
