import re

def patch_file(path):
    with open(path, "r") as f:
        content = f.read()

    # 1. ADD CACHE BUSTER TO URLS
    content = re.sub(
        r"const DATA_URL = '(.*?)';",
        r"const DATA_URL = '\1?v=' + Date.now();",
        content
    )
    content = re.sub(
        r"const DAILY_URL = '(.*?)';",
        r"const DAILY_URL = '\1?v=' + Date.now();",
        content
    )
    content = re.sub(
        r"const HISTORY_URL = '(.*?)';",
        r"const HISTORY_URL = '\1?v=' + Date.now();",
        content
    )

    # 2. REWRITE AGGREGATOR TO BE BULLETPROOF
    # It will try to find data in DAILY, then HISTORY, then RAW SNAPSHOT.
    new_aggregator = """
    function aggregateRangeData(start, end) {
      const aggregated = { exchanges: {} };
      const startTime = start ? start.getTime() : -Infinity;
      const endTime = end ? end.getTime() : Infinity;
      const searchSources = [dailyData, historyData].filter(s => Array.isArray(s));
      
      let foundAny = false;

      searchSources.forEach(source => {
        source.forEach(entry => {
          const dDate = new Date(entry.date || entry.timestamp);
          const dTime = dDate.getTime();
          if (dTime >= startTime && dTime <= endTime && entry.tokens && entry.tokens[selectedToken]) {
            const t = entry.tokens[selectedToken];
            const exData = t.exchanges || {};
            
            // If the source is historyData, it might use 'deployments'
            if (t.deployments) {
              t.deployments.forEach(dep => {
                Object.entries(dep.exchange_flows || {}).forEach(([ex, flows]) => {
                  if (!aggregated.exchanges[ex]) aggregated.exchanges[ex] = { net_flow: 0, inflow: 0, outflow: 0 };
                  aggregated.exchanges[ex].inflow += (flows.inflow || 0);
                  aggregated.exchanges[ex].outflow += (flows.outflow || 0);
                  aggregated.exchanges[ex].net_flow += (flows.net_flow || 0);
                  foundAny = true;
                });
              });
            } else {
              Object.entries(exData).forEach(([ex, flows]) => {
                if (!aggregated.exchanges[ex]) aggregated.exchanges[ex] = { net_flow: 0, inflow: 0, outflow: 0 };
                aggregated.exchanges[ex].inflow += (flows.inflow || flows.in || 0);
                aggregated.exchanges[ex].outflow += (flows.outflow || flows.out || 0);
                aggregated.exchanges[ex].net_flow += (flows.net_flow || flows.net || 0);
                foundAny = true;
              });
            }
          }
        });
      });

      // LAST RESORT FALLBACK: If range is "All Time" and aggregator found nothing, use the latest snapshot
      if (!foundAny && (!start || startTime === -Infinity) && rawData.tokens[selectedToken]) {
        const d = rawData.tokens[selectedToken];
        if (d.deployments) {
          d.deployments.forEach(dep => {
            Object.entries(dep.exchange_flows || {}).forEach(([ex, flows]) => {
              if (!aggregated.exchanges[ex]) aggregated.exchanges[ex] = { net_flow: 0, inflow: 0, outflow: 0 };
              aggregated.exchanges[ex].inflow += (flows.inflow || 0);
              aggregated.exchanges[ex].outflow += (flows.outflow || 0);
              aggregated.exchanges[ex].net_flow += (flows.net_flow || 0);
            });
          });
        }
      }

      return aggregated;
    }
    """
    content = re.sub(r"function aggregateRangeData\(.*?\n    \}", new_aggregator, content, flags=re.DOTALL)

    # 3. FIX UPDATE_DASHBOARD REDUNDANCY
    content = re.sub(
        r"setTimeout\(\(\) => \{ isUpdatingToken = false; \}, 100\);\n  // Force a full-data refresh.*?updateSankey\(rawData\.tokens\[token\]\);",
        "setTimeout(() => { isUpdatingToken = false; }, 100);",
        content,
        flags=re.DOTALL
    )

    with open(path, "w") as f:
        f.write(content)

patch_file("terminal/index.html")
patch_file("index.html")
patch_file("web/terminal.html")
