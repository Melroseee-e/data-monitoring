import re

with open("terminal/index.html", "r") as f:
    content = f.read()

# 1. DISABLE ANIMATIONS FOR INSTANT "FULL STATE"
content = re.sub(
    r"Plotly\.react\(div, plotData, layout, \{displayModeBar: false, responsive: true\}\);",
    "Plotly.react(div, plotData, layout, {displayModeBar: false, responsive: true, staticPlot: false, config: {transition: {duration: 0}}});",
    content
)

content = re.sub(
    r"Plotly\.react\(div, traces, layout, \{displayModeBar: false, responsive: true\}\);",
    "Plotly.react(div, traces, layout, {displayModeBar: false, responsive: true, config: {transition: {duration: 0}}});",
    content
)

# 2. FIX SANKEY NODE SIZE (THINNER NODES, MORE SPACE)
content = re.sub(
    r"node: \{ pad: 15, thickness: 20,",
    "node: { pad: 30, thickness: 10,",
    content
)

# 3. CONSOLIDATE TO ROOT
with open("terminal/index.html", "w") as f:
    f.write(content)
with open("index.html", "w") as f:
    f.write(content)

