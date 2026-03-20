import re

with open("web/terminal.html", "r") as f:
    content = f.read()

# 1. FIX THE "0.00" TABLE BUG:
# In aggregateRangeData, we use inflow, outflow, net_flow.
# In updateExchangeTable, we were checking flows.in, flows.out, flows.net.
# We MUST unify them to use exactly what the aggregator produces.

new_table_func = """function updateExchangeTable(data) {
  const tbody = document.querySelector('#exchangeTable tbody');
  let agg = {};
  
  if (data.deployments) {
    data.deployments.forEach(dep => {
      Object.entries(dep.exchange_flows).forEach(([ex, flows]) => {
        if(!agg[ex]) agg[ex] = {inflow:0, outflow:0, net_flow:0};
        agg[ex].inflow += (flows.inflow || 0);
        agg[ex].outflow += (flows.outflow || 0);
        agg[ex].net_flow += (flows.inflow - flows.outflow);
      });
    });
  } else if (data.exchanges) {
    agg = data.exchanges;
  }
  
  const sortedEx = Object.entries(agg).sort((a,b) => Math.abs(b[1].net_flow || 0) - Math.abs(a[1].net_flow || 0));
  
  tbody.innerHTML = sortedEx.map(([ex, flows]) => {
    const net = flows.net_flow || 0;
    const isPos = net >= 0;
    return `<tr>
      <td style="font-family:var(--font-ui); font-weight:500;">${ex}</td>
      <td class="pos">${formatNum(flows.inflow || 0)}</td>
      <td class="neg">${formatNum(flows.outflow || 0)}</td>
      <td class="${isPos ? 'pos' : 'neg'}">${isPos ? '+' : ''}${formatNum(net)}</td>
    </tr>`;
  }).join('');
}"""

content = re.sub(r"function updateExchangeTable\(data\) \{.*?\}\n\nfunction updateTrendChart", new_table_func + "\n\nfunction updateTrendChart", content, flags=re.DOTALL)

# 2. FIX THE SANKEY DATA KEYS:
new_sankey_func = """function updateSankey(data) {
  const isLight = document.body.classList.contains('theme-light');
  const sankeyNodeColor = isLight ? '#E4E4E7' : '#27272A';
  const sankeyTextColor = isLight ? '#71717A' : '#A1A1AA';

  const nodeLabels = [selectedToken];
  const nodeColors = ['#3B82F6'];
  const linkSources = [];
  const linkTargets = [];
  const linkValues = [];
  const linkColors = [];
  
  let nodeIdx = 1;

  if (data.deployments) {
    data.deployments.forEach(dep => {
      Object.entries(dep.exchange_flows).forEach(([ex, flows]) => {
        nodeLabels.push(ex);
        nodeColors.push(sankeyNodeColor);
        if(flows.inflow > 0) { linkSources.push(nodeIdx); linkTargets.push(0); linkValues.push(flows.inflow); linkColors.push(isLight ? 'rgba(5, 150, 105, 0.4)' : 'rgba(0, 255, 163, 0.4)'); }
        if(flows.outflow > 0) { linkSources.push(0); linkTargets.push(nodeIdx); linkValues.push(flows.outflow); linkColors.push(isLight ? 'rgba(220, 38, 38, 0.4)' : 'rgba(255, 77, 77, 0.4)'); }
        nodeIdx++;
      });
    });
  } else if (data.exchanges) {
    Object.entries(data.exchanges).forEach(([ex, flows]) => {
      nodeLabels.push(ex);
      nodeColors.push(sankeyNodeColor);
      const inf = flows.inflow || 0;
      const outf = flows.outflow || 0;
      if(inf > 0) { linkSources.push(nodeIdx); linkTargets.push(0); linkValues.push(inf); linkColors.push(isLight ? 'rgba(5, 150, 105, 0.4)' : 'rgba(0, 255, 163, 0.4)'); }
      if(outf > 0) { linkSources.push(0); linkTargets.push(nodeIdx); linkValues.push(outf); linkColors.push(isLight ? 'rgba(220, 38, 38, 0.4)' : 'rgba(255, 77, 77, 0.4)'); }
      nodeIdx++;
    });
  }

  if(linkValues.length === 0) {
    Plotly.purge('sankeyChart');
    document.getElementById('sankeyChart').innerHTML = `<div style="padding:20px;color:${sankeyTextColor};text-align:center;">No flow data available for this range</div>`;
    return;
  }

  const plotData = [{
    type: 'sankey', orientation: 'h',
    node: { pad: 80, thickness: 12, line: { color: 'transparent', width: 0 }, label: nodeLabels, color: nodeColors },
    link: { source: linkSources, target: linkTargets, value: linkValues, color: linkColors }
  }];

  const layout = {
    autosize: true, font: { size: 11, color: sankeyTextColor, family: "'Inter', sans-serif" },
    paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
    margin: { l: 40, r: 40, t: 60, b: 60 },
    height: Math.max(300, Math.min(600, nodeIdx * 40)),
    transition: { duration: 0 }
  };

  document.getElementById('sankeyChart').innerHTML = ''; 
  Plotly.newPlot('sankeyChart', plotData, layout, {displayModeBar: false, responsive: true});
  setTimeout(() => Plotly.Plots.resize('sankeyChart'), 500);
}"""

content = re.sub(r"function updateSankey\(data\) \{.*?\}\n\n// Ensure both charts", new_sankey_func + "\n\n// Ensure both charts", content, flags=re.DOTALL)

with open("web/terminal.html", "w") as f:
    f.write(content)
