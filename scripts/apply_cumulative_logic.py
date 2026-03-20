import re

with open("web/terminal.html", "r") as f:
    content = f.read()

# 1. Add initTrendTabs call and new globals
content = re.sub(
    r"let selectedToken = null;\nlet charts = {};",
    r"let selectedToken = null;\nlet charts = {};\nlet currentTrendView = 'daily'; // 'daily' or 'cumulative'",
    content
)

# 2. Add initTrendTabs function definition
init_trend_tabs = """function initTrendTabs() {
  document.querySelectorAll('.trend-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.trend-tab').forEach(t => {
        t.classList.remove('active');
        t.style.borderBottomColor = 'transparent';
        t.style.color = 'var(--text-muted)';
      });
      tab.classList.add('active');
      tab.style.borderBottomColor = 'var(--accent)';
      tab.style.color = 'var(--text-main)';
      currentTrendView = tab.dataset.view;
      if (selectedToken) updateTrendChart(selectedToken);
    });
  });
}
"""
content = re.sub(r"function formatNum", init_trend_tabs + "\nfunction formatNum", content)

# 3. Add initTrendTabs call to init()
content = re.sub(r"async function init\(\) \{\n  initTheme\(\);", "async function init() {\n  initTheme();\n  initTrendTabs();", content)

# 4. Overwrite updateTrendChart with Cumulative support and Sync Logic
new_update_trend_chart = """function updateTrendChart(token) {
  let sourceData = dailyData;
  let hasDataInDaily = dailyData && dailyData.some(d => d.tokens?.[token] && (d.tokens[token].total_inflow > 0 || d.tokens[token].total_outflow > 0));
  
  if (!hasDataInDaily && historyData && Array.isArray(historyData)) {
    sourceData = historyData;
  }

  if(!sourceData || !Array.isArray(sourceData)) return;
  
  let startIndex = 0;
  for (let i = 0; i < sourceData.length; i++) {
    const tData = sourceData[i].tokens?.[token];
    if (tData && (tData.total_inflow > 0 || tData.total_outflow > 0)) {
      startIndex = i;
      break;
    }
  }
  
  const tokenDataList = sourceData.slice(startIndex);

  const dates = [];
  const inflows = [];
  const outflows = [];
  const nets = [];
  const cumulative = [];
  let runningNet = 0;
  
  tokenDataList.forEach(entry => {
    const d = entry.date || entry.timestamp; if(!d) return; dates.push(d);
    const tData = entry.tokens?.[token];
    const inf = tData ? (tData.total_inflow || 0) : 0;
    const outf = tData ? (tData.total_outflow || 0) : 0;
    const net = inf - outf;
    
    inflows.push(inf);
    outflows.push(outf);
    nets.push(net);
    
    runningNet += net;
    cumulative.push(runningNet);
  });

  const isLight = document.body.classList.contains('theme-light');
  const textColor = isLight ? '#71717A' : '#A1A1AA';
  const gridColor = isLight ? '#E4E4E7' : '#18181B';
  const inflowColor = isLight ? '#059669' : '#00FFA3';
  const outflowColor = isLight ? '#DC2626' : '#FF4D4D';
  const netColor = '#3B82F6';

  let plotTraces = [];
  
  if (currentTrendView === 'daily') {
    plotTraces = [
      { x: dates, y: inflows, name: 'Inflow', type: 'bar', marker: { color: inflowColor }, hoverinfo: 'y+name' },
      { x: dates, y: outflows.map(v => -v), name: 'Outflow', type: 'bar', marker: { color: outflowColor }, hoverinfo: 'y+name' },
      { x: dates, y: nets, name: 'Net Flow', type: 'scatter', mode: 'lines', line: { color: netColor, width: 2 }, hoverinfo: 'y+name' }
    ];
  } else {
    plotTraces = [
      { 
        x: dates, y: cumulative, name: 'Cumulative Net Flow', type: 'scatter', mode: 'lines', 
        fill: 'tozeroy', line: { color: netColor, width: 3 },
        fillcolor: isLight ? 'rgba(59, 130, 246, 0.1)' : 'rgba(59, 130, 246, 0.2)',
        hoverinfo: 'y+name' 
      }
    ];
  }

  const layout = {
    autosize: true, barmode: 'relative', paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
    font: { family: "'JetBrains Mono', monospace", color: textColor, size: 11 },
    margin: { l: 60, r: 20, t: 20, b: 20 },
    legend: { orientation: 'h', yanchor: 'bottom', y: 1.02, xanchor: 'right', x: 1 },
    hovermode: 'x unified',
    xaxis: {
      type: 'date', gridcolor: gridColor, zerolinecolor: gridColor,
      rangeslider: { visible: true, borderwidth: 1, bordercolor: gridColor, bgcolor: isLight ? '#F4F4F5' : '#09090B', thickness: 0.1 },
      rangeselector: {
        buttons: [
          { count: 1, label: '1D', step: 'day', stepmode: 'backward' },
          { count: 7, label: '1W', step: 'day', stepmode: 'backward' },
          { count: 1, label: '1M', step: 'month', stepmode: 'backward' },
          { step: 'all', label: 'ALL' }
        ],
        bgcolor: isLight ? '#FFFFFF' : '#18181B', activecolor: isLight ? '#E4E4E7' : '#27272A'
      }
    },
    yaxis: { gridcolor: gridColor, zerolinecolor: gridColor, tickformat: '.2s', autorange: true, fixedrange: false }
  };

  const chartDiv = document.getElementById('trendChart');
  chartDiv.innerHTML = ''; 
  Plotly.newPlot(chartDiv, plotTraces, layout, {displayModeBar: false, responsive: true});

  // Dynamic Scaling & Sync Logic
  chartDiv.on('plotly_relayout', function(eventData) {
    let start, end;
    if (eventData['xaxis.range[0]'] && eventData['xaxis.range[1]']) {
      start = new Date(eventData['xaxis.range[0]']);
      end = new Date(eventData['xaxis.range[1]']);
    } else if (eventData['xaxis.autorange']) {
      Plotly.relayout(chartDiv, { 'yaxis.autorange': true });
      document.getElementById('timeRangeDisplay').style.display = 'none';
      updateExchangeTable(rawData.tokens[selectedToken]);
      updateSankey(rawData.tokens[selectedToken]);
      return;
    } else { return; }

    // Update Time Range Display
    const rangeDisplay = document.getElementById('timeRangeDisplay');
    const fmt = d => d.toISOString().split('T')[0];
    rangeDisplay.innerText = `${fmt(start)} → ${fmt(end)}`;
    rangeDisplay.style.display = 'block';

    // 1. Sync Table & Sankey
    const aggregated = { exchanges: {} };
    const searchSources = [dailyData, historyData].filter(s => Array.isArray(s));
    
    searchSources.forEach(source => {
      source.forEach(day => {
        const dDate = new Date(day.date || day.timestamp);
        if (dDate >= start && dDate <= end && day.tokens[selectedToken]) {
          const t = day.tokens[selectedToken];
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
    });
    
    if (Object.keys(aggregated.exchanges).length > 0) {
      updateExchangeTable(aggregated);
      updateSankey(aggregated);
    }

    // 2. Dynamic Y-axis
    const visibleInflows = [], visibleOutflows = [], visibleNets = [], visibleCums = [];
    dates.forEach((d, i) => {
      const date = new Date(d);
      if (date >= start && date <= end) {
        visibleInflows.push(inflows[i] || 0);
        visibleOutflows.push(outflows[i] || 0);
        visibleNets.push(nets[i] || 0);
        visibleCums.push(cumulative[i] || 0);
      }
    });

    if (visibleInflows.length > 0) {
      let maxVal, minVal;
      if (currentTrendView === 'daily') {
        maxVal = Math.max(...visibleInflows, ...visibleNets);
        minVal = Math.min(...visibleOutflows.map(v => -v), ...visibleNets);
      } else {
        maxVal = Math.max(...visibleCums);
        minVal = Math.min(...visibleCums);
      }
      const span = maxVal - minVal;
      const padding = span === 0 ? 1 : span * 0.15;
      Plotly.relayout(chartDiv, { 'yaxis.range': [minVal - padding, maxVal + padding], 'yaxis.autorange': false });
    }
  });
}"""

content = re.sub(r"function updateTrendChart\(token\) \{.*?\n\}", new_update_trend_chart, content, flags=re.DOTALL)

with open("web/terminal.html", "w") as f:
    f.write(content)
