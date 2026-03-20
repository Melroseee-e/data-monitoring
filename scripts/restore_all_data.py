import re

with open("web/terminal.html", "r") as f:
    content = f.read()

# 1. Restore global variables
globals_block = """const DATA_URL = '../data/latest_data.json';
const DAILY_URL = '../data/daily_summary.json';
const HISTORY_URL = '../data/history_summary.json';

let rawData = null;
let dailyData = null;
let historyData = null;
let selectedToken = null;
let charts = {};
let currentTrendView = 'daily'; // 'daily' or 'cumulative'"""

content = re.sub(r"const DATA_URL = .*?let currentTrendView = .*?;", globals_block, content, flags=re.DOTALL)

# 2. Restore init() fetching
init_func = """async function init() {
  initTheme();
  initTrendTabs();
  try {
    const [dRes, dailyRes, hRes] = await Promise.all([
      fetch(DATA_URL).catch(()=>null),
      fetch(DAILY_URL).catch(()=>null),
      fetch(HISTORY_URL).catch(()=>null)
    ]);
    if(dRes && dRes.ok) rawData = await dRes.json();
    if(dailyRes && dailyRes.ok) dailyData = await dailyRes.json();
    if(hRes && hRes.ok) historyData = await hRes.json();
    
    // Pre-calculate cumulative stats for all tokens to fix 0.00 displays
    if (rawData && rawData.tokens && dailyData) {
      Object.keys(rawData.tokens).forEach(symbol => {
        let totalIn = 0, totalOut = 0;
        dailyData.forEach(day => {
          const t = day.tokens[symbol];
          if (t) {
            totalIn += (t.total_inflow || 0);
            totalOut += (t.total_outflow || 0);
          }
        });
        if (totalIn > rawData.tokens[symbol].total_inflow) {
          rawData.tokens[symbol].total_inflow = totalIn;
          rawData.tokens[symbol].total_outflow = totalOut;
          rawData.tokens[symbol].net_flow = totalIn - totalOut;
        }
      });
    }
    
    if(rawData && rawData.metadata) {
      document.getElementById('lastUpdated').innerText = 'UPDATED: ' + rawData.metadata.last_updated;
    }
    
    renderTokenList();
    
    document.getElementById('tokenSearch').addEventListener('input', (e) => {
      renderTokenList(e.target.value.toLowerCase());
    });
    
  } catch(e) {
    console.error("Init error", e);
  }
}"""

content = re.sub(r"async function init\(\) \{.*?\}", init_func, content, flags=re.DOTALL)

with open("web/terminal.html", "w") as f:
    f.write(content)
