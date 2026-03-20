import re

with open("web/terminal.html", "r") as f:
    content = f.read()

# 1. Fix the sync logic keys and date comparison
# We use getTime() for robust range comparison
new_sync_logic = """    // 1. Sync Table & Sankey
    const aggregated = { exchanges: {} };
    const searchSources = [dailyData, historyData].filter(s => Array.isArray(s));
    
    const startTime = start.getTime();
    const endTime = end.getTime();

    searchSources.forEach(source => {
      source.forEach(day => {
        const dDate = new Date(day.date || day.timestamp);
        const dTime = dDate.getTime();
        
        if (dTime >= startTime && dTime <= endTime && day.tokens[selectedToken]) {
          const t = day.tokens[selectedToken];
          const exData = t.exchanges || {}; 
          // If no .exchanges, check if it's from historyData which has no exchange breakdown
          // but we prioritize showing what we have.
          Object.entries(exData).forEach(([ex, flows]) => {
            if (!aggregated.exchanges[ex]) aggregated.exchanges[ex] = { net: 0, in: 0, out: 0 };
            aggregated.exchanges[ex].in += (flows.inflow || flows.in || 0);
            aggregated.exchanges[ex].out += (flows.outflow || flows.out || 0);
            aggregated.exchanges[ex].net += (flows.net_flow || flows.net || 0);
          });
        }
      });
    });"""

content = re.sub(
    r"// 1\. Sync Table & Sankey\n    const aggregated = \{ exchanges: \{\} \};.*?// 2\. Dynamic Y-axis",
    new_sync_logic + "\n\n    // 2. Dynamic Y-axis",
    content,
    flags=re.DOTALL
)

# 2. Fix updateExchangeTable display keys
content = re.sub(
    r"\${formatNum\(flows\.in \|\| flows\.total_inflow \|\| 0\)\}",
    r"${formatNum(flows.in || flows.inflow || 0)}",
    content
)
content = re.sub(
    r"\${formatNum\(flows\.out \|\| flows\.total_outflow \|\| 0\)\}",
    r"${formatNum(flows.out || flows.outflow || 0)}",
    content
)

# 3. Ensure BIRB and PUMP start correctly
# Improve startIndex search to be more sensitive
content = re.sub(
    r"if \(tData && \(tData\.total_inflow > 0 \|\| tData\.total_outflow > 0\)\)",
    r"if (tData && (Math.abs(tData.total_inflow) > 0.01 || Math.abs(tData.total_outflow) > 0.01))",
    content
)

with open("web/terminal.html", "w") as f:
    f.write(content)
