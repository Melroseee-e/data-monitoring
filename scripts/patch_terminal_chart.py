import re

with open("web/terminal.html", "r") as f:
    content = f.read()

# 1. Update the pane header text to remove the hardcoded (30D) since we will show all data
content = re.sub(
    r"<span>Flow History \(30D\)</span>",
    r"<span>Flow History (All Time) <small style='color:var(--text-muted); font-weight:normal; margin-left:8px;'>(Scroll / Pinch to Zoom)</small></span>",
    content
)

# 2. Add chartjs-plugin-zoom to head
zoom_plugin = """<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/hammerjs@2.0.8/hammer.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1/dist/chartjs-plugin-zoom.min.js"></script>"""
content = re.sub(r'<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>', zoom_plugin, content)

# 3. Modify updateTrendChart to load all data and configure the zoom plugin
new_chart_func = """function updateTrendChart(token) {
  if(!historyData || !historyData.daily_summary) return;
  
  // Use all dates instead of slice(-30)
  const dates = Object.keys(historyData.daily_summary).sort();
  const inflows = [];
  const outflows = [];
  const nets = [];
  
  dates.forEach(d => {
    const dayData = historyData.daily_summary[d]?.tokens?.[token];
    if(dayData) {
      inflows.push(dayData.inflow || 0);
      outflows.push(dayData.outflow || 0);
      nets.push((dayData.inflow || 0) - (dayData.outflow || 0));
    } else {
      inflows.push(0); outflows.push(0); nets.push(0);
    }
  });

  const ctx = document.getElementById('trendChart').getContext('2d');
  if(charts.trend) charts.trend.destroy();
  
  charts.trend = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: dates, // Full YYYY-MM-DD
      datasets: [
        {
          type: 'line',
          label: 'Net Flow',
          data: nets,
          borderColor: '#3B82F6',
          borderWidth: 2,
          tension: 0,
          pointRadius: 0,
          pointHoverRadius: 4,
          fill: false,
          yAxisID: 'y'
        },
        {
          type: 'bar',
          label: 'Inflow',
          data: inflows,
          backgroundColor: '#00FFA3',
          yAxisID: 'y'
        },
        {
          type: 'bar',
          label: 'Outflow',
          data: outflows.map(v => -v), // display downwards
          backgroundColor: '#FF4D4D',
          yAxisID: 'y'
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      scales: {
        x: { 
          stacked: true,
          ticks: { maxTicksLimit: 12 } // Prevent overlapping x-axis labels
        },
        y: { 
          stacked: true,
          position: 'right',
          ticks: { callback: v => formatNum(v) }
        }
      },
      plugins: {
        legend: { position: 'top', align: 'end', labels: { boxWidth: 10 } },
        tooltip: {
          backgroundColor: '#09090B',
          borderColor: '#27272A',
          borderWidth: 1,
          titleFont: { family: 'Inter' },
          bodyFont: { family: 'JetBrains Mono' },
          callbacks: {
            label: function(context) {
              let label = context.dataset.label || '';
              if (label) { label += ': '; }
              if (context.parsed.y !== null) { label += formatNum(Math.abs(context.parsed.y)); }
              return label;
            }
          }
        },
        zoom: {
          pan: {
            enabled: true,
            mode: 'x',
            modifierKey: null,
          },
          zoom: {
            wheel: {
              enabled: true,
              speed: 0.1
            },
            pinch: {
              enabled: true
            },
            mode: 'x',
            drag: {
              enabled: true,
              backgroundColor: 'rgba(59, 130, 246, 0.2)',
              borderColor: '#3B82F6',
              borderWidth: 1
            }
          }
        }
      }
    }
  });
}"""

content = re.sub(r"function updateTrendChart\(token\) \{.*?(?=function updateSankey)", new_chart_func + "\n\n", content, flags=re.DOTALL)

with open("web/terminal.html", "w") as f:
    f.write(content)

