import re

with open("web/terminal.html", "r") as f:
    content = f.read()

# 1. FIX THE "DOUBLE CLICK" DATA RESET BUG:
# Instead of falling back to rawData.tokens (snapshot), fallback to full history aggregation.
content = re.sub(
    r"Plotly\.relayout\(chartDiv, \{ 'yaxis\.autorange': true \}\);\n      document\.getElementById\('timeRangeDisplay'\)\.style\.display = 'none';\n      updateExchangeTable\(rawData\.tokens\[selectedToken\]\);\n      updateSankey\(rawData\.tokens\[selectedToken\]\);",
    r"Plotly.relayout(chartDiv, { 'yaxis.autorange': true });\n      document.getElementById('timeRangeDisplay').style.display = 'none';\n      const fullAgg = aggregateRangeData(null, null);\n      updateExchangeTable(fullAgg);\n      updateSankey(fullAgg);",
    content
)

# 2. RESTORE SANKEY HOVER (Routing Tool):
# Correct the Plotly.react config argument and ensure hover is enabled.
content = re.sub(
    r"Plotly\.react\('sankeyChart', plotData, layout, \{displayModeBar: false, responsive: true, config: \{transition: \{duration: 0\}\}\}\);",
    r"Plotly.react('sankeyChart', plotData, layout, {displayModeBar: false, responsive: true, hovermode: 'closest'});",
    content
)

# 3. DISABLE DOUBLE-CLICK RESET IF IT'S CAUSING CONFUSION (Optional but good for stability)
# Or just ensure it works correctly (which Step 1 does). 
# Let's also disable the default plotly double-click to prevent unexpected jumps.
content = re.sub(
    r"Plotly\.react\(chartDiv, plotTraces, layout, \{displayModeBar: false, responsive: true\}\);",
    r"Plotly.react(chartDiv, plotTraces, layout, {displayModeBar: false, responsive: true, doubleClick: 'reset+autosize'});",
    content
)

# 4. FIX SANKEY NODE Proportions one more time
content = re.sub(
    r"node: \{ pad: dynamicPadding, thickness: 15,",
    r"node: { pad: Math.min(dynamicPadding, 30), thickness: 18,",
    content
)

with open("web/terminal.html", "w") as f:
    f.write(content)
