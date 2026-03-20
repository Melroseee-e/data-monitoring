import re

with open("web/terminal.html", "r") as f:
    content = f.read()

# 1. FIX THE AGGREGATOR TO HANDLE NULL START/END PROPERLY
# The issue is that start.getTime() fails if start is null.
new_aggregator_logic = """    function aggregateRangeData(start, end) {
      const aggregated = { exchanges: {} };
      const startTime = start ? new Date(start).getTime() : -Infinity;
      const endTime = end ? new Date(end).getTime() : Infinity;
      const searchSources = [dailyData, historyData].filter(s => Array.isArray(s));
      
      searchSources.forEach(source => {
        source.forEach(entry => {
          const dDate = new Date(entry.date || entry.timestamp);
          const dTime = dDate.getTime();
          if (dTime >= startTime && dTime <= endTime && entry.tokens && entry.tokens[selectedToken]) {
            const t = entry.tokens[selectedToken];
            const exData = t.exchanges || {}; 
            Object.entries(exData).forEach(([ex, flows]) => {
              if (!aggregated.exchanges[ex]) aggregated.exchanges[ex] = { net_flow: 0, inflow: 0, outflow: 0 };
              aggregated.exchanges[ex].inflow += (flows.inflow || flows.in || 0);
              aggregated.exchanges[ex].outflow += (flows.outflow || flows.out || 0);
              aggregated.exchanges[ex].net_flow += (flows.net_flow || flows.net || 0);
            });
          }
        });
      });
      return aggregated;
    }"""

content = re.sub(r"function aggregateRangeData\(start, end\) \{.*?return aggregated;\n    \}", new_aggregator_logic, content, flags=re.DOTALL)

# 2. FIX THE DOUBLE CLICK HANDLER
# Ensure we don't crash on nulls and call the aggregator safely.
content = re.sub(
    r"const fullAgg = aggregateRangeData\(null, null\);",
    "const fullAgg = aggregateRangeData(null, null);",
    content
)

# 3. ENSURE SANKEY DOES NOT PURGE IF REACT IS CALLED
# Plotly.react handles clearing. Manual purge + innerHTML='' can break subsequent Plotly calls if not timed right.
content = re.sub(
    r"if\(linkValues\.length === 0\) \{\n    Plotly\.purge\('sankeyChart'\);\n    document\.getElementById\('sankeyChart'\)\.innerHTML = `<div style=\"padding:20px;color:\${sankeyTextColor};text-align:center;\">No flow data available for this range</div>`;\n    return;\n  \}",
    r"""if(linkValues.length === 0) {
    Plotly.purge('sankeyChart');
    document.getElementById('sankeyChart').innerHTML = `<div style="padding:20px;color:${sankeyTextColor};text-align:center;">No flow data available for this range</div>`;
    return;
  }""",
    content
)

with open("web/terminal.html", "w") as f:
    f.write(content)
