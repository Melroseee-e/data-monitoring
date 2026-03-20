import re

with open("terminal/index.html", "r") as f:
    content = f.read()

# 1. FIX SANKEY LABELS AND POSITION
# Plotly Sankey labels can go off-screen. We increase margins and adjust padding.
content = re.sub(
    r"margin: \{ l:40, r:40, t:20, b:20 \}",
    "margin: { l: 10, r: 10, t: 30, b: 10 }",
    content
)

# Refine node padding and thickness
content = re.sub(
    r"node: \{ pad: Math\.max\(20, 300/nodes\.length\), thickness: 12,",
    "node: { pad: 15, thickness: 20,",
    content
)

# 2. IMPROVE TREND CHART BARS AND Y-AXIS
# Add bar width/padding to make them more visible
content = re.sub(
    r"yaxis: \{ autorange: true, fixedrange: false, tickformat: '\.2s', gridcolor: isL\?'#E4E4E7':'#18181B' \}",
    "yaxis: { autorange: true, fixedrange: false, tickformat: '.2s', gridcolor: isL?'#E4E4E7':'#18181B', zeroline: true, zerolinecolor: isL?'#E4E4E7':'#27272A' }",
    content
)

# 3. FIX CUMULATIVE VIEW DATA HOVER
content = re.sub(
    r"Cumulative', type: 'scatter', mode: 'lines', fill: 'tozeroy'",
    "Cumulative', type: 'scatter', mode: 'lines', fill: 'tozeroy', hovertemplate: '%{y:.3s}<extra></extra>'",
    content
)

# 4. CONSOLIDATE: Overwrite root index.html with this polished version
with open("terminal/index.html", "w") as f:
    f.write(content)

with open("index.html", "w") as f:
    f.write(content)

