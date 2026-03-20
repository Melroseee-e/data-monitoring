import re

with open("web/terminal.html", "r") as f:
    content = f.read()

# 1. Improved aggregation logic that handles BOTH formats correctly
universal_aggregator = """
    function aggregateRangeData(start, end) {
      const aggregated = { exchanges: {} };
      const startTime = start ? start.getTime() : -Infinity;
      const endTime = end ? end.getTime() : Infinity;
      const searchSources = [dailyData, historyData].filter(s => Array.isArray(s));
      
      searchSources.forEach(source => {
        source.forEach(entry => {
          const dDate = new Date(entry.date || entry.timestamp);
          const dTime = dDate.getTime();
          if (dTime >= startTime && dTime <= endTime && entry.tokens && entry.tokens[selectedToken]) {
            const t = entry.tokens[selectedToken];
            
            // Handle dailyData format
            if (t.exchanges) {
              Object.entries(t.exchanges).forEach(([ex, flows]) => {
                if (!aggregated.exchanges[ex]) aggregated.exchanges[ex] = { net_flow: 0, inflow: 0, outflow: 0 };
                aggregated.exchanges[ex].inflow += (flows.inflow || flows.in || 0);
                aggregated.exchanges[ex].outflow += (flows.outflow || flows.out || 0);
                aggregated.exchanges[ex].net_flow += (flows.net_flow || flows.net || 0);
              });
            } 
            // Handle historyData / raw format
            else if (t.deployments) {
              t.deployments.forEach(dep => {
                Object.entries(dep.exchange_flows || {}).forEach(([ex, flows]) => {
                  if (!aggregated.exchanges[ex]) aggregated.exchanges[ex] = { net_flow: 0, inflow: 0, outflow: 0 };
                  aggregated.exchanges[ex].inflow += (flows.inflow || 0);
                  aggregated.exchanges[ex].outflow += (flows.outflow || 0);
                  aggregated.exchanges[ex].net_flow += (flows.net_flow || 0);
                });
              });
            }
          }
        });
      });
      return aggregated;
    }
"""

# Insert the helper function before updateDashboard
content = re.sub(r"function updateDashboard", universal_aggregator + "\nfunction updateDashboard", content)

# 2. Simplify updateDashboard to use the aggregator
new_update_dashboard = """function updateDashboard() {
  isUpdatingToken = true;
  if(!rawData || !selectedToken) return;
  const d = rawData.tokens[selectedToken];
  if(!d) return;
  
  // Header
  document.getElementById('headerTitle').innerHTML = `${selectedToken} <span class="badge">${d.deployments ? (d.deployments[0]?.chain || '') : ''}</span>`;
  document.getElementById('kpiInflow').innerText = formatNum(d.total_inflow);
  document.getElementById('kpiOutflow').innerText = formatNum(d.total_outflow);
  
  const netEl = document.getElementById('kpiNet');
  netEl.innerText = (d.net_flow >= 0 ? '+' : '') + formatNum(d.net_flow);
  netEl.className = 'kpi-mini-val ' + (d.net_flow >= 0 ? 'pos' : 'neg');
  
  // Initial render with ALL-TIME aggregated data (from start of time)
  document.getElementById('timeRangeDisplay').style.display = 'none';
  const fullHistory = aggregateRangeData(null, null);
  
  if (Object.keys(fullHistory.exchanges).length > 0) {
    updateExchangeTable(fullHistory);
    updateSankey(fullHistory);
  } else {
    // Last resort fallback
    updateExchangeTable(d);
    updateSankey(d);
  }
  
  updateTrendChart(selectedToken);
}"""

content = re.sub(r"function updateDashboard\(.*?\n\}", new_update_dashboard, content, flags=re.DOTALL)

# 3. Simplify the relayout listener to use the aggregator
new_relayout_sync = """    // 1. Sync Table & Sankey
    const aggregated = aggregateRangeData(start, end);
    
    if (Object.keys(aggregated.exchanges).length > 0) {
      updateExchangeTable(aggregated);
      updateSankey(aggregated);
    }"""

content = re.sub(
    r"// 1\. Sync Table & Sankey\n    const aggregated = \{ exchanges: \{\} \};.*?updateSankey\(aggregated\);\n    \}",
    new_relayout_sync,
    content,
    flags=re.DOTALL
)

with open("web/terminal.html", "w") as f:
    f.write(content)
