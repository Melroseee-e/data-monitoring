import re
import os

with open("web/terminal.html", "r") as f:
    content = f.read()

# 1. Remove Chart.js zoom plugins and Chart.js since we will use Plotly for everything.
# Actually we can keep Chart.js if anything else uses it, but terminal only uses Sankey and Trend.
# Let's just remove the Chart.js canvas and replace it with a div for Plotly.
content = re.sub(
    r'<canvas id="trendChart"></canvas>',
    r'<div id="trendChart" style="width:100%; height:100%;"></div>',
    content
)

# 2. Update updateTrendChart to use Plotly
plotly_trend_func = """function updateTrendChart(token) {
  if(!historyData || !Array.isArray(historyData)) return;
  
  let startIndex = 0;
  for (let i = 0; i < historyData.length; i++) {
    const tData = historyData[i].tokens?.[token];
    if (tData && (tData.total_inflow > 0 || tData.total_outflow > 0)) {
      startIndex = i;
      break;
    }
  }
  
  const tokenDataList = historyData.slice(startIndex);

  const dates = [];
  const inflows = [];
  const outflows = [];
  const nets = [];
  
  tokenDataList.forEach(entry => {
    // Plotly handles ISO strings well natively
    dates.push(entry.timestamp);

    const tData = entry.tokens?.[token];
    if(tData) {
      inflows.push(tData.total_inflow || 0);
      outflows.push(tData.total_outflow || 0);
      nets.push((tData.total_inflow || 0) - (tData.total_outflow || 0));
    } else {
      inflows.push(0); outflows.push(0); nets.push(0);
    }
  });

  const isLight = document.body.classList.contains('theme-light');
  const textColor = isLight ? '#71717A' : '#A1A1AA';
  const gridColor = isLight ? '#E4E4E7' : '#18181B';
  const inflowColor = isLight ? '#059669' : '#00FFA3';
  const outflowColor = isLight ? '#DC2626' : '#FF4D4D';
  const netColor = '#3B82F6';

  const traceInflow = {
    x: dates,
    y: inflows,
    name: 'Inflow',
    type: 'bar',
    marker: { color: inflowColor },
    hoverinfo: 'y+name'
  };

  const traceOutflow = {
    x: dates,
    y: outflows.map(v => -v), // point downwards
    name: 'Outflow',
    type: 'bar',
    marker: { color: outflowColor },
    hoverinfo: 'y+name'
  };

  const traceNet = {
    x: dates,
    y: nets,
    name: 'Net Flow',
    type: 'scatter',
    mode: 'lines',
    line: { color: netColor, width: 2 },
    hoverinfo: 'y+name'
  };

  const layout = {
    autosize: true,
    barmode: 'relative',
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { family: "'JetBrains Mono', monospace", color: textColor, size: 11 },
    margin: { l: 50, r: 20, t: 20, b: 20 },
    legend: { orientation: 'h', yanchor: 'bottom', y: 1.02, xanchor: 'right', x: 1 },
    hovermode: 'x unified',
    xaxis: {
      type: 'date',
      gridcolor: gridColor,
      zerolinecolor: gridColor,
      rangeslider: { visible: true, borderwidth: 1, bordercolor: gridColor, bgcolor: isLight ? '#F4F4F5' : '#09090B' },
      rangeselector: {
        buttons: [
          { count: 1, label: '1D', step: 'day', stepmode: 'backward' },
          { count: 7, label: '1W', step: 'day', stepmode: 'backward' },
          { count: 1, label: '1M', step: 'month', stepmode: 'backward' },
          { step: 'all', label: 'ALL' }
        ],
        bgcolor: isLight ? '#FFFFFF' : '#18181B',
        activecolor: isLight ? '#E4E4E7' : '#27272A'
      }
    },
    yaxis: {
      gridcolor: gridColor,
      zerolinecolor: gridColor,
      tickformat: '.2s'
    }
  };

  document.getElementById('trendChart').innerHTML = ''; // Clear old chart
  Plotly.newPlot('trendChart', [traceInflow, traceOutflow, traceNet], layout, {displayModeBar: false, responsive: true});
}

function updateSankey(data) {
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

  data.deployments.forEach(dep => {
    Object.entries(dep.exchange_flows).forEach(([ex, flows]) => {
      nodeLabels.push(ex);
      nodeColors.push(sankeyNodeColor);
      
      if(flows.inflow > 0) {
        linkSources.push(nodeIdx);
        linkTargets.push(0);
        linkValues.push(flows.inflow);
        linkColors.push(isLight ? 'rgba(5, 150, 105, 0.4)' : 'rgba(0, 255, 163, 0.4)');
      }
      if(flows.outflow > 0) {
        linkSources.push(0);
        linkTargets.push(nodeIdx);
        linkValues.push(flows.outflow);
        linkColors.push(isLight ? 'rgba(220, 38, 38, 0.4)' : 'rgba(255, 77, 77, 0.4)');
      }
      nodeIdx++;
    });
  });

  if(linkValues.length === 0) {
    document.getElementById('sankeyChart').innerHTML = `<div style="padding:20px;color:${sankeyTextColor};text-align:center;">No flow data available</div>`;
    return;
  }

  const plotData = [{
    type: 'sankey',
    orientation: 'h',
    node: {
      pad: 30, // Increased padding to prevent giant blocks
      thickness: 15,
      line: { color: 'transparent', width: 0 },
      label: nodeLabels,
      color: nodeColors
    },
    link: {
      source: linkSources,
      target: linkTargets,
      value: linkValues,
      color: linkColors
    }
  }];

  const layout = {
    autosize: true,
    font: { size: 11, color: sankeyTextColor, family: "'Inter', sans-serif" },
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    margin: { l: 20, r: 20, t: 40, b: 40 }
  };

  document.getElementById('sankeyChart').innerHTML = ''; 
  Plotly.newPlot('sankeyChart', plotData, layout, {displayModeBar: false, responsive: true});
}

// Ensure both charts resize correctly
window.addEventListener('resize', () => {
  if (document.getElementById('sankeyChart').data) Plotly.Plots.resize('sankeyChart');
  if (document.getElementById('trendChart').data) Plotly.Plots.resize('trendChart');
});
"""

# Replace both updateTrendChart and updateSankey logic
content = re.sub(r"function updateTrendChart\(token\) \{.*?\n\}\n\nfunction updateSankey\(data\) \{.*?\n\}", plotly_trend_func, content, flags=re.DOTALL)

# Hide Reset Zoom button since Plotly provides rangeslider and rangeselector natively
content = re.sub(
    r'<button id="resetZoomBtn".*?</button>',
    '',
    content
)

# Also fix the updateDashboard call so that switching theme re-renders Plotly correctly
content = re.sub(
    r"updateDashboard\(\); // Re-render charts with new theme colors",
    r"if (selectedToken) { updateDashboard(); }",
    content
)


with open("web/terminal.html", "w") as f:
    f.write(content)

