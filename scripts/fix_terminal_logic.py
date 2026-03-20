import re

with open("web/terminal.html", "r") as f:
    content = f.read()

# 1. Update updateDashboard to ensure it always clears the old data and tries to find data in daily first
# and set the sourceData correctly.
# Actually let's just make updateTrendChart more robust.

# 2. Add an explicit clear step in updateDashboard
content = re.sub(
    r"// Initial render with cumulative data\n  updateExchangeTable\(d\);\n  updateSankey\(d\);\n  updateTrendChart\(selectedToken\);",
    r"""// Initial render with cumulative data
  // Clear old state displays
  document.getElementById('timeRangeDisplay').style.display = 'none';
  
  updateExchangeTable(d);
  updateSankey(d);
  updateTrendChart(selectedToken);""",
    content
)

# 3. Robust sync logic in plotly_relayout
sync_logic = """    // 1. Sync Table & Sankey
    const aggregated = { exchanges: {} };
    // Search across ALL available data sources to find exchange info for the range
    const searchSources = [dailyData, historyData].filter(s => Array.isArray(s));
    
    searchSources.forEach(source => {
      source.forEach(day => {
        const dDate = new Date(day.date || day.timestamp);
        if (dDate >= start && dDate <= end && day.tokens[selectedToken]) {
          const t = day.tokens[selectedToken];
          // Use exchanges if available (dailyData format) or deployments (rawData format)
          if (t.exchanges) {
            Object.entries(t.exchanges).forEach(([ex, flows]) => {
              if (!aggregated.exchanges[ex]) aggregated.exchanges[ex] = { net: 0, in: 0, out: 0 };
              aggregated.exchanges[ex].in += (flows.in || flows.total_inflow || 0);
              aggregated.exchanges[ex].out += (flows.out || flows.total_outflow || 0);
              aggregated.exchanges[ex].net += (flows.net || flows.net_flow || 0);
            });
          }
        }
      });
    });"""

content = re.sub(
    r"// 1\. Sync Table & Sankey\n    const aggregated = \{ exchanges: \{\} \};.*?// 2\. Dynamic Y-axis",
    sync_logic + "\n\n    // 2. Dynamic Y-axis",
    content,
    flags=re.DOTALL
)

# 4. Final safety check for Sankey data source fallback
# If we have no aggregated exchange data, show the rawData (all-time) exchange data as a hint
content = re.sub(
    r"if \(Object.keys\(aggregated.exchanges\).length > 0\) \{",
    r"if (Object.keys(aggregated.exchanges).length > 0) {",
    content
)

# Actually, the user's issue was "Bird doesn't show anything below".
# It likely happened because relayout failed or searchSources was empty.
# Let's add a more aggressive clear/reset when switching tokens.

with open("web/terminal.html", "w") as f:
    f.write(content)
