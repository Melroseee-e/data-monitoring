import re

with open("web/terminal.html", "r") as f:
    content = f.read()

# 1. Force use allData for syncing to ensure we don't miss any token
# The issue is that BIRB might only be in historyData but the sync logic was biased or sourceData was wrong.
# Let's just aggregate everything properly in the dashboard.

# 2. Add high contrast styles for headers
content = re.sub(
    r"\.pane-header \{",
    ".pane-header { color: var(--text-main) !important; font-weight: 800 !important; font-size: 13px !important; ",
    content
)

# 3. Fix the Sankey empty state text when it actually HAS data but Plotly hasn't drawn yet
content = re.sub(
    r"document\.getElementById\('sankeyChart'\)\.innerHTML = '';",
    "document.getElementById('sankeyChart').innerHTML = '<div style=\"padding:20px;text-align:center;\">Loading Routing Data...</div>';",
    content
)

# 4. Fix the inflow/outflow zero issue in table
# The aggregated data in relayout used 'in', 'out' but the table function looks for 'inflow', 'outflow'.
# Let's unify EVERYTHING to 'inflow', 'outflow', 'net_flow'.
unify_logic = """          if (t.exchanges) {
            Object.entries(t.exchanges).forEach(([ex, flows]) => {
              if (!aggregated.exchanges[ex]) aggregated.exchanges[ex] = { net_flow: 0, inflow: 0, outflow: 0 };
              aggregated.exchanges[ex].inflow += (flows.inflow || flows.in || 0);
              aggregated.exchanges[ex].outflow += (flows.outflow || flows.out || 0);
              aggregated.exchanges[ex].net_flow += (flows.net_flow || flows.net || 0);
            });
          }"""

content = re.sub(
    r"if \(t\.exchanges\) \{.*?aggregated\.exchanges\[ex\]\.net \+= \(flows\.net \|\| flows\.net_flow \|\| 0\);\n            \}\n          \}",
    unify_logic,
    content,
    flags=re.DOTALL
)

# 5. Fix updateExchangeTable to use unified keys
table_fix = """      <td style="font-family:var(--font-ui); font-weight:500;">${ex}</td>
      <td class="pos">${formatNum(flows.inflow || 0)}</td>
      <td class="neg">${formatNum(flows.outflow || 0)}</td>
      <td class="${isPos ? 'pos' : 'neg'}">${isPos ? '+' : ''}${formatNum(flows.net_flow || 0)}</td>"""

content = re.sub(
    r'<td style="font-family:var\(--font-ui\); font-weight:500;">\${ex}</td>.*?formatNum\(flows\.net \|\| flows\.net_flow \|\| 0\)\}\</td>',
    table_fix,
    content,
    flags=re.DOTALL
)

# 6. Fix updateSankey to use unified keys
sankey_fix = """  } else if (data.exchanges) {
    Object.entries(data.exchanges).forEach(([ex, flows]) => {
      nodeLabels.push(ex);
      nodeColors.push(sankeyNodeColor);
      if(flows.inflow > 0) { linkSources.push(nodeIdx); linkTargets.push(0); linkValues.push(flows.inflow); linkColors.push(isLight ? 'rgba(5, 150, 105, 0.4)' : 'rgba(0, 255, 163, 0.4)'); }
      if(flows.outflow > 0) { linkSources.push(0); linkTargets.push(nodeIdx); linkValues.push(flows.outflow); linkColors.push(isLight ? 'rgba(220, 38, 38, 0.4)' : 'rgba(255, 77, 77, 0.4)'); }
      nodeIdx++;
    });
  }"""

content = re.sub(
    r"\} else if \(data\.exchanges\) \{.*?nodeIdx\+\+;\n    \}\n  \}",
    sankey_fix,
    content,
    flags=re.DOTALL
)

with open("web/terminal.html", "w") as f:
    f.write(content)
